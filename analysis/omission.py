"""
Omission score — section 6.6.

Entity-based omission: reference_weights = canonicalized entities across all
sources covering the event, weighted by how many sources mention each one —
so omitting something every other source considered central counts more
than omitting a detail one outlet mentioned in passing.

Also includes the KeyBERT topic-overlap variant the spec calls for
alongside it, to catch omitted *themes* that named entities miss (e.g. a
source that never names "inflation" as an entity but never engages with
the topic either).
"""
from keybert import KeyBERT

_kw_model = None


def get_kw_model():
    global _kw_model
    if _kw_model is None:
        _kw_model = KeyBERT()
    return _kw_model


def build_reference_weights(entities_by_source: dict[str, set[str]]) -> dict[str, float]:
    """
    entities_by_source: {source_name: {canonical_entity, ...}, ...}
    Returns {entity: weight}, weight = fraction of sources that mention it.
    """
    n_sources = len(entities_by_source)
    if n_sources == 0:
        return {}
    counts: dict[str, int] = {}
    for entities in entities_by_source.values():
        for e in entities:
            counts[e] = counts.get(e, 0) + 1
    return {e: c / n_sources for e, c in counts.items()}


def omission_score(source_entities: set[str], reference_weights: dict[str, float]) -> float | None:
    """
    Weighted fraction of "reference importance" a source fails to mention.
    Returns None (not 0.0) if there's no reference to compare against at
    all — an event with only one source has nothing to omit relative to,
    and 0.0 there would misleadingly read as "complete coverage."
    """
    total_weight = sum(reference_weights.values())
    if total_weight == 0:
        return None
    missing_weight = sum(w for e, w in reference_weights.items() if e not in source_entities)
    return missing_weight / total_weight


def missing_entities(source_entities: set[str], reference_weights: dict[str, float], top_n: int = 20) -> list[dict]:
    """For the OmissionPanel drill-down: which entities is this source missing, ranked by importance."""
    missing = [
        {"entity": e, "weight": w}
        for e, w in reference_weights.items()
        if e not in source_entities
    ]
    return sorted(missing, key=lambda m: -m["weight"])[:top_n]


def topic_overlap_score(source_text: str, reference_texts: list[str], top_n: int = 10) -> float | None:
    """
    KeyBERT-based topic overlap: extract top_n keyphrases from this source
    and from the union of all other sources' text, and score by Jaccard
    overlap. Complements the entity-based score above — this catches
    thematic omission where the same *entities* appear but the source never
    engages with a topic (e.g. "the economic fallout") the others do.
    """
    if not source_text.strip() or not reference_texts:
        return None
    kw_model = get_kw_model()

    source_keywords = {kw for kw, _ in kw_model.extract_keywords(source_text, top_n=top_n)}
    reference_keywords: set[str] = set()
    for text in reference_texts:
        reference_keywords |= {kw for kw, _ in kw_model.extract_keywords(text, top_n=top_n)}

    if not reference_keywords:
        return None

    missing = reference_keywords - source_keywords
    return len(missing) / len(reference_keywords)
