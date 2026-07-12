"""
Entity-level sentiment — section 6.4.

Pretrained, used as-is (cardiffnlp/twitter-roberta-base-sentiment-latest).
No fine-tuning here — a pretrained 3-class model is the right call unless
you have thousands of labeled entity-sentiment pairs, which this project
doesn't (the only labeled data BASIL gives you is bias spans, used in 6.7).
"""
from transformers import pipeline

_sentiment_pipe = None

POLARITY = {"positive": 1, "neutral": 0, "negative": -1}


def get_pipe():
    global _sentiment_pipe
    if _sentiment_pipe is None:
        _sentiment_pipe = pipeline(
            "sentiment-analysis",
            model="cardiffnlp/twitter-roberta-base-sentiment-latest",
        )
    return _sentiment_pipe


def entity_sentiment(sentences: list[str], entity: str) -> float | None:
    """
    Average sentiment (-1..1) across every sentence mentioning `entity`.
    Returns None if the entity isn't mentioned at all — a missing score
    means "not discussed", it should never be silently treated as 0/neutral.
    """
    relevant = [s for s in sentences if entity.lower() in s.lower()]
    if not relevant:
        return None
    scores = get_pipe()(relevant)
    return sum(POLARITY[s["label"].lower()] * s["score"] for s in scores) / len(scores)


def entity_sentiment_batch(sentences: list[str], entities: list[str]) -> dict[str, float | None]:
    """Convenience wrapper for scoring every canonical entity in one article at once."""
    return {entity: entity_sentiment(sentences, entity) for entity in entities}
