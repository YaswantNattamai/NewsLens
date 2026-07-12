"""
BASIL loader — section 6.1.

Parses BASIL's article triplets and bias-span annotations into the common
internal format the rest of the pipeline expects:

    {event_id, source, raw_text, bias_spans: [...]}

IMPORTANT — verify against your actual download before trusting this file:
BASIL is distributed as one JSON file per article, grouped into per-event
directories, but the exact key names have drifted across releases/forks of
the dataset. This loader assumes the commonly-used layout:

    data/basil/<event_id>/<source>.json
    {
      "title": "...",
      "url": "...",
      "body-paragraphs": [["sentence one", "sentence two", ...], ...],
      "word-level-annotations": [
        {"start": 123, "end": 145, "bias": "Lexical", "text": "..."},
        ...
      ]
    }

If your downloaded copy uses different keys (some releases nest sentences
under "sentences" instead of "body-paragraphs", or store spans under
"annotations" instead of "word-level-annotations"), adjust `_extract_text`
and `_extract_bias_spans` below — the rest of the pipeline only depends on
the shape returned by `load_event`, not on these internals.
"""
import json
import os
from dataclasses import dataclass, field
from pathlib import Path

BASIL_DATA_DIR = Path(os.getenv("BASIL_DATA_DIR", "./data/basil"))


@dataclass
class BiasSpan:
    start: int
    end: int
    label: str
    text: str


@dataclass
class BasilArticle:
    event_id: str
    source: str
    raw_text: str
    url: str | None
    bias_spans: list[BiasSpan] = field(default_factory=list)


def _extract_text(article_json: dict) -> str:
    paragraphs = article_json.get("body-paragraphs") or article_json.get("sentences") or []
    # body-paragraphs is a list of paragraphs, each a list of sentence strings
    sentences = []
    for para in paragraphs:
        if isinstance(para, list):
            sentences.extend(para)
        else:
            sentences.append(para)
    return " ".join(s.strip() for s in sentences if s and s.strip())


def _extract_bias_spans(article_json: dict) -> list[BiasSpan]:
    raw_spans = article_json.get("word-level-annotations") or article_json.get("annotations") or []
    spans = []
    for s in raw_spans:
        try:
            spans.append(BiasSpan(
                start=s.get("start", -1),
                end=s.get("end", -1),
                label=s.get("bias", s.get("label", "unknown")),
                text=s.get("text", ""),
            ))
        except AttributeError:
            continue
    return spans


def list_event_ids(basil_dir: Path = BASIL_DATA_DIR) -> list[str]:
    if not basil_dir.exists():
        raise FileNotFoundError(
            f"BASIL_DATA_DIR '{basil_dir}' not found. Download BASIL and point "
            f"BASIL_DATA_DIR at it (see README)."
        )
    return sorted(p.name for p in basil_dir.iterdir() if p.is_dir())


def load_event(event_id: str, basil_dir: Path = BASIL_DATA_DIR) -> list[BasilArticle]:
    """Load all source articles (typically Fox / HuffPost / NYT) for one BASIL event."""
    event_dir = basil_dir / event_id
    if not event_dir.exists():
        raise FileNotFoundError(f"No such BASIL event directory: {event_dir}")

    articles = []
    for json_path in sorted(event_dir.glob("*.json")):
        source = json_path.stem  # filename without extension, e.g. "fox"
        with open(json_path, "r", encoding="utf-8") as f:
            article_json = json.load(f)
        articles.append(BasilArticle(
            event_id=event_id,
            source=source,
            raw_text=_extract_text(article_json),
            url=article_json.get("url"),
            bias_spans=_extract_bias_spans(article_json),
        ))
    return articles


def load_all_events(basil_dir: Path = BASIL_DATA_DIR) -> dict[str, list[BasilArticle]]:
    return {eid: load_event(eid, basil_dir) for eid in list_event_ids(basil_dir)}
