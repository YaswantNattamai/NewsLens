"""
Per-event pipeline orchestration. Not called out as a separate file in the
spec's repo structure, but the API layer (6.10) needs something that wires
6.3-6.6 together and persists the results — this is that glue.

Run this once per event when it's loaded (BASIL events can be precomputed
in bulk ahead of time, per the "demo should feel instant" requirement in
section 3).
"""
import os
from itertools import combinations

from preprocessing.clean import to_sentences
from analysis.ner import extract_entities, canonicalize_across_sources
from analysis.sentiment import entity_sentiment_batch
from analysis.framing import align_and_score
from analysis.omission import build_reference_weights, omission_score, missing_entities, topic_overlap_score
from storage.db import get_conn, dumps

# Optional — only used if a fine-tuned checkpoint is actually configured.
# See analysis/bias_classifier.py and README section 10 for how to get one
# (train on Kaggle, download the `final/` folder, point this at it).
BIAS_MODEL_DIR = os.getenv("BIAS_MODEL_DIR")


def analyze_event(event_id: int) -> None:
    with get_conn() as conn:
        articles = conn.execute(
            "SELECT id, source, clean_text FROM articles WHERE event_id = %s",
            (event_id,),
        ).fetchall()

    if len(articles) < 2:
        raise ValueError(f"Event {event_id} has fewer than 2 articles — nothing to compare.")

    # --- per-article: sentences, entities, canonical entity set ---
    per_source = {}
    raw_entities_by_source = {}
    for art in articles:
        sentences = to_sentences(art["clean_text"])
        raw_entities_by_source[art["source"]] = extract_entities(art["clean_text"])
        per_source[art["source"]] = {
            "article_id": art["id"],
            "clean_text": art["clean_text"],
            "sentences": sentences,
        }

    entities_result = canonicalize_across_sources(raw_entities_by_source)
    for source, entities in entities_result.items():
        per_source[source]["entities"] = entities
        per_source[source]["entity_set"] = {e["entity"] for e in entities}

    # --- entity sentiment, written straight to entity_mentions ---
    with get_conn() as conn:
        for source, data in per_source.items():
            sentiments = entity_sentiment_batch(data["sentences"], list(data["entity_set"]))
            for e in data["entities"]:
                conn.execute(
                    """INSERT INTO entity_mentions
                       (article_id, canonical_entity, entity_type, mention_count, sentiment_score)
                       VALUES (%s, %s, %s, %s, %s)""",
                    (data["article_id"], e["entity"], e["type"], e["count"], sentiments.get(e["entity"])),
                )

    # --- bias classifier inference — OPTIONAL, skipped entirely if BIAS_MODEL_DIR
    # isn't set. Training (Kaggle) and inference (here) are separate steps on
    # purpose; this never trains anything itself. ---
    if BIAS_MODEL_DIR:
        from analysis.bias_classifier import predict_bias
        with get_conn() as conn:
            for source, data in per_source.items():
                predictions = predict_bias(data["sentences"], BIAS_MODEL_DIR)
                for p in predictions:
                    conn.execute(
                        """INSERT INTO sentence_bias_predictions (article_id, sentence, biased, probability)
                           VALUES (%s, %s, %s, %s)""",
                        (data["article_id"], p["sentence"], p["biased"], p["probability"]),
                    )

    # --- omission: reference weights across all sources in this event ---
    entities_by_source = {s: d["entity_set"] for s, d in per_source.items()}
    reference_weights = build_reference_weights(entities_by_source)

    # Topic-overlap (KeyBERT) is computed once per source against the union of
    # every OTHER source's text, same "global relative to the event" scope as
    # the entity-based omission score above — not recomputed per pair.
    topic_overlap_by_source = {}
    for source, data in per_source.items():
        other_texts = [d["clean_text"] for s, d in per_source.items() if s != source]
        topic_overlap_by_source[source] = topic_overlap_score(data["clean_text"], other_texts)

    # --- pairwise framing + omission, written to bias_scores ---
    with get_conn() as conn:
        for source_a, source_b in combinations(per_source.keys(), 2):
            data_a, data_b = per_source[source_a], per_source[source_b]

            framing = align_and_score(data_a["sentences"], data_b["sentences"])

            omission_a = omission_score(data_a["entity_set"], reference_weights)
            omission_b = omission_score(data_b["entity_set"], reference_weights)
            missing_a = missing_entities(data_a["entity_set"], reference_weights)
            missing_b = missing_entities(data_b["entity_set"], reference_weights)

            conn.execute(
                """INSERT INTO bias_scores
                   (event_id, source_a, source_b, framing_score,
                    omission_score_a, omission_score_b,
                    topic_overlap_score_a, topic_overlap_score_b,
                    aligned_pairs, missing_entities_a, missing_entities_b)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                (
                    event_id, source_a, source_b,
                    framing["score"] if framing else None,
                    omission_a, omission_b,
                    topic_overlap_by_source[source_a], topic_overlap_by_source[source_b],
                    dumps(framing["aligned_pairs"] if framing else []),
                    dumps(missing_a), dumps(missing_b),
                ),
            )
