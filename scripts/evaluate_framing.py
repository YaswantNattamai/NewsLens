"""
Framing-metric validation — the "trust" step (spec section 7, RQ1).

The framing score is a heuristic: it measures how divergently two sources
phrase their *most similar* sentence pairs. Before anyone reads a number off
the UI and believes it, we owe them evidence that the number tracks something
real. The one piece of ground truth we have is BASIL's human bias-span
annotations, so this script asks a single, falsifiable question:

    Do the sentence alignments our framing metric flags as MORE divergent
    coincide with sentences human annotators marked as biased?

Method (all against BASIL, no live data):
  1. For every event, split each source's article into sentences.
  2. For every source pair, run the real `align_and_score` and collect each
     aligned pair's divergence (1 - cosine similarity).
  3. Label each aligned pair "human-biased" if either of its two sentences
     contains a BASIL bias-span's annotated text (substring match — the same
     approximate labeling the bias classifier uses, since exact char offsets
     depend on an unverified file format; see PIPELINE_OVERVIEW.md).
  4. Report whether divergence separates the biased pairs from the rest:
       - ROC AUC of divergence as a predictor of the human label
       - point-biserial correlation
       - mean divergence in each group, with counts

Honest reading of the output:
  - AUC ~0.5 / r ~0  → the framing score does NOT track human bias; treat the
    UI number as "sources phrase things differently," nothing stronger.
  - AUC > ~0.6 / r positive & non-trivial n → modest but real signal; still a
    lower bound, still not a verdict, but not noise either.
  This is deliberately a modest bar. The goal is an honest, citable number,
  not a headline.

Run:  python -m scripts.evaluate_framing
      python -m scripts.evaluate_framing --threshold 0.4 --min-span-chars 12
"""
from __future__ import annotations

import argparse
import csv
import sys
from itertools import combinations

# These imports pull in spaCy + sentence-transformers; keep them lazy-ish by
# importing at module top only what's cheap, and the heavy bits inside main so
# `--help` stays instant.


def _span_texts(article, min_span_chars: int) -> list[str]:
    """Annotated bias-span strings long enough to match on without false hits."""
    out = []
    for s in getattr(article, "bias_spans", []) or []:
        t = (getattr(s, "text", "") or "").strip().lower()
        if len(t) >= min_span_chars:
            out.append(t)
    return out


def _is_biased(sentence: str, span_texts: list[str]) -> bool:
    s = sentence.lower()
    return any(t in s for t in span_texts)


def _point_biserial(divergences, labels):
    """Pearson r between a continuous var and a binary label, via numpy."""
    import numpy as np

    x = np.asarray(divergences, dtype=float)
    y = np.asarray(labels, dtype=float)
    if x.std() == 0 or y.std() == 0:
        return float("nan")
    return float(np.corrcoef(x, y)[0, 1])


def evaluate(threshold: float, min_span_chars: int, limit_events: int | None):
    from ingestion.basil_loader import list_event_ids, load_event
    from preprocessing.clean import to_sentences
    from analysis.framing import align_and_score

    try:
        event_ids = list_event_ids()
    except FileNotFoundError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)

    if limit_events:
        event_ids = event_ids[:limit_events]

    rows = []  # per aligned pair: (event, pair, divergence, biased)
    events_with_labels = 0
    total_spans = 0

    for eid in event_ids:
        articles = load_event(eid)
        if len(articles) < 2:
            continue

        sents = {a.source: to_sentences(a.raw_text) for a in articles}
        spans = {a.source: _span_texts(a, min_span_chars) for a in articles}
        n_spans = sum(len(v) for v in spans.values())
        total_spans += n_spans
        if n_spans:
            events_with_labels += 1

        for sa, sb in combinations(sents.keys(), 2):
            result = align_and_score(sents[sa], sents[sb], threshold=threshold)
            if not result:
                continue
            for p in result["aligned_pairs"]:
                divergence = 1.0 - p["similarity"]
                biased = _is_biased(p["sentence_a"], spans[sa]) or _is_biased(
                    p["sentence_b"], spans[sb]
                )
                rows.append((eid, f"{sa}|{sb}", divergence, biased))
        print(f"  processed event {eid} ({len(articles)} sources)", file=sys.stderr)

    if not rows:
        print("No aligned pairs produced — nothing to evaluate. Is BASIL loaded?",
              file=sys.stderr)
        sys.exit(1)

    divergences = [r[2] for r in rows]
    labels = [1 if r[3] else 0 for r in rows]
    n_pos = sum(labels)
    n = len(labels)

    import numpy as np

    div = np.asarray(divergences)
    pos_mean = div[np.asarray(labels) == 1].mean() if n_pos else float("nan")
    neg_mean = div[np.asarray(labels) == 0].mean() if n_pos < n else float("nan")
    r_pb = _point_biserial(divergences, labels)

    auc = float("nan")
    if 0 < n_pos < n:
        from sklearn.metrics import roc_auc_score
        auc = roc_auc_score(labels, divergences)

    # --- report ---
    print("\n" + "=" * 68)
    print("FRAMING METRIC vs. BASIL HUMAN BIAS SPANS")
    print("=" * 68)
    print(f"events evaluated        : {len(event_ids)} "
          f"({events_with_labels} had usable bias spans)")
    print(f"similarity threshold    : {threshold}")
    print(f"min span length (chars) : {min_span_chars}")
    print(f"total bias spans used   : {total_spans}")
    print(f"aligned pairs (samples) : {n}")
    print(f"  ... human-biased      : {n_pos} ({100*n_pos/n:.1f}%)")
    print("-" * 68)
    print(f"mean divergence, biased : {pos_mean:.4f}")
    print(f"mean divergence, other  : {neg_mean:.4f}")
    print(f"point-biserial r        : {r_pb:.4f}")
    print(f"ROC AUC (div -> biased) : {auc:.4f}")
    print("-" * 68)
    # Plain-language verdict — deliberately cautious.
    if np.isnan(auc):
        verdict = "Not enough label variation to judge (need both biased and non-biased pairs)."
    elif auc >= 0.60 and n_pos >= 20:
        verdict = ("Modest but real signal: more-divergent alignments do tend to be the "
                   "human-flagged ones. Still a lower bound, still not a verdict.")
    elif auc >= 0.55:
        verdict = ("Weak signal. Divergence leans the right way but is close to chance -- "
                   "present the UI number as 'phrasing differs', nothing stronger.")
    else:
        verdict = ("No meaningful signal against human labels. Treat the framing number as "
                   "descriptive only; do NOT imply it measures bias.")
    print("VERDICT:", verdict)
    print("=" * 68)

    # --- CSV for the record ---
    out_path = "framing_evaluation.csv"
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["event_id", "source_pair", "divergence", "human_biased"])
        for eid, pair, d, b in rows:
            w.writerow([eid, pair, f"{d:.6f}", int(b)])
    print(f"\nPer-pair rows written to {out_path}", file=sys.stderr)


def main():
    ap = argparse.ArgumentParser(description="Validate the framing metric against BASIL bias spans.")
    ap.add_argument("--threshold", type=float, default=0.5,
                    help="similarity floor passed to align_and_score (default 0.5)")
    ap.add_argument("--min-span-chars", type=int, default=10,
                    help="ignore bias spans shorter than this many chars (default 10)")
    ap.add_argument("--limit-events", type=int, default=None,
                    help="evaluate only the first N events (for a quick check)")
    args = ap.parse_args()
    evaluate(args.threshold, args.min_span_chars, args.limit_events)


if __name__ == "__main__":
    main()
