# NewsLens — what the current pipeline actually does

This is a snapshot of the real state of the code, not the aspirational spec.
Anything here that sounds like a caveat is a caveat — read it before
presenting results from this as if it were a validated system.

## The end-to-end flow, as it runs today

Triggered by one call: `POST /events` with a `basil_event_id`.

```
BASIL JSON files on disk
        │
        ▼
ingestion/basil_loader.py        parses articles + human bias-span annotations
        │
        ▼
Postgres: events, articles       raw article text stored
        │
        ▼
analysis/pipeline.py             orchestrates everything below, per event
        │
        ├─► preprocessing/clean.py         sentence-splits each article
        │
        ├─► analysis/ner.py                extracts PERSON/ORG/GPE entities,
        │                                  fuzzy-merges near-duplicate names
        │                                  (spaCy en_core_web_sm — pretrained)
        │
        ├─► analysis/sentiment.py          scores each entity's sentiment per
        │                                  source (cardiffnlp RoBERTa — pretrained)
        │
        ├─► analysis/bias_classifier.py    OPTIONAL: only runs if BIAS_MODEL_DIR
        │   (predict_bias only)            is set to a fine-tuned checkpoint you
        │                                  downloaded from the Kaggle notebook.
        │                                  Skipped entirely otherwise — this is
        │                                  the ONE model in the whole pipeline
        │                                  that isn't pretrained-and-ready; it
        │                                  has to be trained by you first.
        │
        ├─► analysis/framing.py            aligns each source pair's sentences
        │                                  by embedding similarity, scores
        │                                  divergence (MiniLM — pretrained)
        │
        └─► analysis/omission.py           two signals, both computed:
                                            (a) entity-based: which sources
                                                miss entities others covered
                                            (b) KeyBERT topic-overlap: which
                                                sources miss themes others
                                                covered, even without a named
                                                entity involved
        │
        ▼
Postgres: entity_mentions, bias_scores, sentence_bias_predictions
        │
        ▼
FastAPI GET endpoints                      frontend reads from here
        │
        ▼
React frontend                             renders everything below
```

## Models — which ones actually run, right now

| Model | Runs on every event? | Trained by you? |
|---|---|---|
| spaCy `en_core_web_sm` (NER) | **Yes, always** | No — pretrained |
| `cardiffnlp/twitter-roberta-base-sentiment-latest` (entity sentiment) | **Yes, always** | No — pretrained |
| `sentence-transformers/all-MiniLM-L6-v2` (framing alignment) | **Yes, always** | No — pretrained |
| KeyBERT (topic-overlap omission) | **Yes, always** | No — pretrained embeddings internally |
| `bert-base-uncased` / `roberta-base` / `distilbert-base-uncased` (bias classifier) | **Only if `BIAS_MODEL_DIR` is set** | **Yes — this is the Kaggle notebook's job** |

Four of the five models work out of the box with no setup beyond
`pip install` — they download their weights automatically the first time
they're called. The fifth (bias classifier) requires you to run the Kaggle
notebook, pick a winning checkpoint, download it, and point `BIAS_MODEL_DIR`
at the downloaded folder. Until you do that, the "Bias signal" panel in the
frontend will always show an empty state — that's expected, not a bug.

## What each API endpoint actually returns

| Endpoint | Backed by | Always populated? |
|---|---|---|
| `GET /basil-events` | files on disk under `BASIL_DATA_DIR` | if BASIL is downloaded |
| `POST /events` | loads + runs the full pipeline on one event | — |
| `GET /events` | events already analyzed in this DB | after first `POST /events` |
| `GET /events/{id}/articles` | `articles` table | yes |
| `GET /events/{id}/entities` | `entity_mentions` table | yes |
| `GET /events/{id}/sentiment` | `entity_mentions.sentiment_score` | yes |
| `GET /events/{id}/framing` | `bias_scores` table | yes, but score can be `null` ("not comparable") if no sentence pair cleared the similarity floor |
| `GET /events/{id}/omission` | `bias_scores` table (entity + topic-overlap columns) | yes |
| `GET /events/{id}/bias` | `sentence_bias_predictions` table | **only if `BIAS_MODEL_DIR` was set when the event was analyzed** |

## What's genuinely NOT built yet

- **Live ingestion** (GDELT / NewsAPI / Google News RSS) — section 4.3 in the
  spec, explicitly lowest priority there too. The app only works with
  pre-loaded BASIL events; there's no "search a live topic" path.
- **Narrative clustering** (section 6.8) — the `ClusterView` component and
  the KMeans clustering logic don't exist yet.
- **Evaluation scripts** (section 7) — correlating the framing score against
  BASIL's human bias-span labels, manual omission labeling, adjusted Rand
  index for clustering. None of this is automated; you'd do it by hand or
  write a notebook against the data already sitting in Postgres.

## Known rough edges worth knowing about

- **BASIL's exact JSON key names are unverified** (`ingestion/basil_loader.py`
  and the Kaggle notebook both flag this in their docstrings) — check your
  actual downloaded files' keys before trusting the loader.
- **Framing score is a lower bound**, not a complete framing measure — it
  only tells you how different the *most similar* sentence pair is, not the
  overall framing gap. This is by design, not a bug, but it's easy to
  over-read the number if you forget the caveat.
- **Omission and topic-overlap scores are computed once per source** (relative
  to the whole event) but stored on every pairwise row that source appears
  in `bias_scores` — the frontend's `OmissionPanel` collapses this back down
  to one bar per source; if you query the table directly, don't be surprised
  to see the same value repeated across rows.
- **The bias classifier's sentence labels are approximate** — a sentence is
  labeled "biased" if an annotated span's text appears as a substring of it,
  not via BASIL's original character offsets (which depend on an unverified
  file format). Good enough to train on, but worth stating as a limitation
  in a report.
