CREATE TABLE IF NOT EXISTS events (
    id SERIAL PRIMARY KEY,
    topic TEXT NOT NULL,
    source_event_id TEXT UNIQUE,   -- BASIL's own event id, for idempotent re-loading
    created_at TIMESTAMP DEFAULT now()
);

CREATE TABLE IF NOT EXISTS articles (
    id SERIAL PRIMARY KEY,
    event_id INT REFERENCES events(id) ON DELETE CASCADE,
    source TEXT NOT NULL,          -- e.g. 'fox', 'huffpost', 'nyt', or a live outlet name
    url TEXT,
    raw_text TEXT,
    clean_text TEXT,
    lean TEXT                      -- live ingestion: left/center/right/unknown; NULL for BASIL
);
CREATE INDEX IF NOT EXISTS idx_articles_event_id ON articles(event_id);

-- Added after the initial release for the live-ingestion path; ADD COLUMN
-- IF NOT EXISTS keeps init_schema() idempotent on pre-existing databases.
ALTER TABLE articles ADD COLUMN IF NOT EXISTS lean TEXT;

CREATE TABLE IF NOT EXISTS entity_mentions (
    id SERIAL PRIMARY KEY,
    article_id INT REFERENCES articles(id) ON DELETE CASCADE,
    canonical_entity TEXT NOT NULL,
    entity_type TEXT,              -- PERSON / ORG / GPE / ...
    mention_count INT DEFAULT 1,
    sentiment_score FLOAT
);
CREATE INDEX IF NOT EXISTS idx_entity_mentions_article_id ON entity_mentions(article_id);
CREATE INDEX IF NOT EXISTS idx_entity_mentions_entity ON entity_mentions(canonical_entity);

CREATE TABLE IF NOT EXISTS bias_scores (
    id SERIAL PRIMARY KEY,
    event_id INT REFERENCES events(id) ON DELETE CASCADE,
    source_a TEXT,
    source_b TEXT,
    framing_score FLOAT,
    omission_score_a FLOAT,        -- entity-based: source_a's omission relative to the union of all sources
    omission_score_b FLOAT,
    topic_overlap_score_a FLOAT,   -- KeyBERT-based: catches omitted themes named-entity omission misses
    topic_overlap_score_b FLOAT,
    aligned_pairs JSONB,           -- [{sentence_a, sentence_b, similarity}], populated by the framing stage
    missing_entities_a JSONB,      -- entities present elsewhere but missing from source_a
    missing_entities_b JSONB
);
CREATE INDEX IF NOT EXISTS idx_bias_scores_event_id ON bias_scores(event_id);

-- Populated only if BIAS_MODEL_DIR is configured and points at a fine-tuned
-- checkpoint (see analysis/bias_classifier.py + README section 10) — this
-- is the RQ2 classifier's *inference* output, separate from the training
-- code that produces the checkpoint in the first place. If no model is
-- configured, this table simply stays empty and the /bias endpoint returns
-- an empty list rather than erroring.
CREATE TABLE IF NOT EXISTS sentence_bias_predictions (
    id SERIAL PRIMARY KEY,
    article_id INT REFERENCES articles(id) ON DELETE CASCADE,
    sentence TEXT NOT NULL,
    biased BOOLEAN NOT NULL,
    probability FLOAT NOT NULL     -- model's confidence in the predicted class
);
CREATE INDEX IF NOT EXISTS idx_sentence_bias_article_id ON sentence_bias_predictions(article_id);
