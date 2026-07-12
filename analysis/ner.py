"""
Entity extraction + type-aware canonicalization — section 6.3.

"Modi", "Narendra Modi", "PM Modi" need to collapse to one canonical entity,
or both the entity frequency table and the omission score break. Fuzzy
matching is restricted to same-type pairs so an ORG never gets merged into
an unrelated common noun that happens to look similar.
"""
from collections import Counter
import re
from rapidfuzz import fuzz

from preprocessing.clean import get_nlp

KEEP_TYPES = {"PERSON", "ORG", "GPE"}  # matches the dashboard grouping in the spec
_STRAY_EDGE_CHARS = ' \t\n"\u201c\u201d\'\u2019'


def extract_entities(text: str) -> list[tuple[str, str]]:
    """Raw (text, label) pairs from spaCy, filtered to the types the dashboard cares about and stripped of stray quotes."""
    nlp = get_nlp()
    doc = nlp(text)
    cleaned = []
    for ent in doc.ents:
        if ent.label_ not in KEEP_TYPES:
            continue
        surface = ent.text.strip(_STRAY_EDGE_CHARS)
        if surface:
            cleaned.append((surface, ent.label_))
    return cleaned


def _person_tokens(text: str) -> set[str]:
    """Normalized token set for surname-matching, e.g. 'Barack Obama's' -> {'barack', 'obama'}."""
    no_possessive = re.sub(r"[\u2019']s\b", "", text)
    no_punct = re.sub(r"[^\w\s]", "", no_possessive)
    return {t.lower() for t in no_punct.split() if len(t) > 1}


def canonicalize(entities: list[tuple[str, str]], threshold: int = 85) -> dict[tuple[str, str], str]:
    """
    Map each (text, label) mention to a canonical surface form, matching only
    within the same entity type. Returns a lookup from every original mention
    to its canonical string.
    """
    canonical: dict[tuple[str, str], str] = {}
    seen: list[tuple[str, str]] = []
    for text, label in entities:
        match = next(
            (s for s, l in seen if l == label and fuzz.token_sort_ratio(text, s) > threshold),
            None,
        )
        if not match and label == "PERSON":
            text_tokens = _person_tokens(text)
            if text_tokens:
                match = next(
                    (
                        s for s, l in seen
                        if l == label
                        and (text_tokens <= _person_tokens(s) or _person_tokens(s) <= text_tokens)
                    ),
                    None,
                )
        canonical[(text, label)] = match or text
        if not match:
            seen.append((text, label))
    return canonical


def entity_frequencies(text: str, threshold: int = 85) -> list[dict]:
    """
    Full pipeline for one article: extract -> canonicalize -> count.
    Returns rows shaped for the entity_mentions table / EntityTable component:
    [{entity, type, count}, ...]
    """
    raw_entities = extract_entities(text)
    canon_map = canonicalize(raw_entities, threshold=threshold)

    counts: Counter[tuple[str, str]] = Counter()
    for (text_, label), canon in canon_map.items():
        counts[(canon, label)] += raw_entities.count((text_, label))

    return [
        {"entity": entity, "type": label, "count": count}
        for (entity, label), count in sorted(counts.items(), key=lambda kv: -kv[1])
    ]


def canonicalize_across_sources(
    entities_by_source: dict[str, list[tuple[str, str]]], threshold: int = 85
) -> dict[str, list[dict]]:
    """
    Same as canonicalize(), but pooled across every source in the event first,
    so the same real-world entity gets the same canonical string everywhere —
    e.g. fox's 'Trump' and hpo's 'Donald Trump' merge into one row, instead of
    each source's independent canonicalize() pass picking its own spelling.
    """
    pooled = [ent for ents in entities_by_source.values() for ent in ents]
    canon_map = canonicalize(pooled, threshold=threshold)

    results = {}
    for source, entities in entities_by_source.items():
        counts = Counter()
        for ent in entities:
            canon = canon_map[ent]
            counts[(canon, ent[1])] += 1
        results[source] = [
            {"entity": entity, "type": label, "count": count}
            for (entity, label), count in sorted(counts.items(), key=lambda kv: -kv[1])
        ]
    return results
