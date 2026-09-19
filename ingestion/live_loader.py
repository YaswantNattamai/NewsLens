"""
Live ingestion — Phase 1.

Mirrors ingestion/basil_loader.py, but instead of reading pre-grouped article
triplets off disk it assembles an "event" on the fly from live news:

    query string ("the topic a user typed")
        │
        ▼
    GDELT Doc 2.0 API   → recent articles about the query, as {url, domain, title}
        │
        ▼
    one article per outlet (domain)   → we compare OUTLETS, not individual stories,
                                         and the downstream pipeline keys off a
                                         unique `source` label per article
        │
        ▼
    readability-lxml    → clean body text from each article's HTML
        │
        ▼
    wire-copy dedup     → drop near-identical bodies (AP/Reuters syndication)
                          so framing scores reflect real editorial difference
        │
        ▼
    list[LiveArticle]   → same shape api.main already inserts for BASIL

The output objects expose .source / .url / .raw_text (like BasilArticle) plus
.lean, so the API insert path barely changes and the whole existing analysis
pipeline (NER → sentiment → framing → omission → clustering) runs unmodified.

No API key required: GDELT's Doc API is open. `requests` fetches both the
GDELT query and each article page; `readability-lxml` extracts body text.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field

import requests

from ingestion.sources import lookup, lean_rank, LEAN_UNKNOWN

log = logging.getLogger("newslens.live")

GDELT_DOC_API = "https://api.gdeltproject.org/api/v2/doc/doc"

# A browser-ish UA; some outlets 403 the default python-requests UA.
_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)

# Bodies shorter than this are almost always nav chrome / paywall stubs, not
# a real article — drop them rather than feed the pipeline junk.
MIN_ARTICLE_CHARS = 400

# Above this cosine similarity two bodies from different outlets are treated
# as the same wire copy, and the later one is dropped.
WIRE_COPY_SIM = 0.95


@dataclass
class LiveArticle:
    source: str           # unique display label per event, e.g. "Fox News"
    url: str
    raw_text: str
    domain: str
    lean: str             # left / center / right / unknown (see ingestion.sources)
    title: str | None = None
    bias_spans: list = field(default_factory=list)  # always empty for live; kept for shape parity


class LiveIngestError(RuntimeError):
    """Raised when a live query can't be turned into a comparable event."""


# ---------------------------------------------------------------------------
# GDELT query
# ---------------------------------------------------------------------------
# Common words that add no retrieval value and, worse, would each have to
# appear literally in an article under GDELT's implicit-AND semantics. Dropping
# them turns "fifa and argentina favouritism" into a fifa AND argentina AND
# favouritism keyword search instead of a doomed exact-phrase match.
_STOPWORDS = {
    "a", "an", "the", "and", "or", "of", "in", "on", "for", "to", "is", "are",
    "was", "were", "be", "with", "about", "vs", "versus", "at", "by", "as",
    "its", "it", "this", "that", "over", "into",
}


def _build_query(query: str) -> str:
    """
    Turn a user's topic into a GDELT query.

    GDELT treats space-separated terms as an implicit AND (every term must
    appear), which already keeps results focused on one story WITHOUT forcing
    an exact-phrase match. So: honor an explicit "quoted phrase" if the user
    typed one, otherwise strip stopwords and AND the remaining keywords. A bare
    quoted-phrase wrap (the old behavior) was too strict — a 4-word descriptive
    query almost never appears verbatim, so it returned nothing.
    """
    q = query.strip()
    if not q:
        raise LiveIngestError("Empty query.")

    # Respect a deliberate phrase search.
    if q.startswith('"') and q.endswith('"') and len(q) > 2:
        return q

    words = [w for w in q.split() if w.lower() not in _STOPWORDS]
    if not words:                       # query was all stopwords — fall back
        words = q.split()
    return " ".join(words)


def _gdelt_search(query: str, timespan: str, maxrecords: int) -> list[dict]:
    params = {
        "query": f"{_build_query(query)} sourcelang:english",
        "mode": "ArtList",
        "format": "json",
        "maxrecords": str(maxrecords),
        "sort": "DateDesc",
        "timespan": timespan,
    }

    # GDELT throttles hard (~1 req / 5s, HTTP 429) AND is frequently slow to
    # respond (10-20s is normal). So we use a generous read timeout and retry
    # on BOTH a throttle and a timeout, turning transient slowness into a short
    # wait instead of a user-facing failure.
    resp = None
    last_err = None
    for attempt in range(3):
        try:
            resp = requests.get(
                GDELT_DOC_API, params=params, headers={"User-Agent": _UA}, timeout=60
            )
        except requests.Timeout as e:
            last_err = e
            if attempt < 2:
                time.sleep(3)
                continue
            raise LiveIngestError(
                "GDELT is responding very slowly right now (request timed out). "
                "Wait a moment and try again."
            ) from e
        except requests.RequestException as e:
            raise LiveIngestError(f"Could not reach GDELT: {e}") from e
        if resp.status_code == 429 and attempt < 2:
            time.sleep(5 * (attempt + 1))
            continue
        break

    if resp.status_code == 429:
        raise LiveIngestError(
            "GDELT is rate-limiting right now (HTTP 429). Wait a few seconds and try again."
        )
    if resp.status_code != 200:
        raise LiveIngestError(f"GDELT returned HTTP {resp.status_code}.")

    # GDELT sometimes answers with a plain-text error instead of JSON
    # (e.g. a too-short query). Surface that clearly rather than crashing.
    try:
        payload = resp.json()
    except ValueError:
        msg = resp.text.strip()[:200] or "non-JSON response"
        raise LiveIngestError(f"GDELT could not process that query: {msg}")

    return payload.get("articles", []) or []


# ---------------------------------------------------------------------------
# Article body extraction
# ---------------------------------------------------------------------------
def _extract_body(url: str) -> str:
    """Fetch an article URL and reduce it to plain body text. '' on any failure."""
    try:
        resp = requests.get(url, headers={"User-Agent": _UA}, timeout=20)
        resp.raise_for_status()
    except requests.RequestException as e:
        log.info("fetch failed for %s: %s", url, e)
        return ""

    html = resp.text
    try:
        from readability import Document
        import lxml.html

        summary_html = Document(html).summary(html_partial=True)
        text = lxml.html.fromstring(summary_html).text_content()
    except Exception as e:  # readability/lxml can throw on odd markup
        log.info("extraction failed for %s: %s", url, e)
        return ""

    # Collapse whitespace; readability leaves a lot of it.
    return " ".join(text.split())


# ---------------------------------------------------------------------------
# Wire-copy dedup
# ---------------------------------------------------------------------------
def _dedup_wire_copy(articles: list[LiveArticle]) -> list[LiveArticle]:
    """
    Drop near-duplicate bodies from DIFFERENT outlets (syndicated AP/Reuters
    copy). Reuses the framing MiniLM model that's already loaded downstream, so
    no new model cost. If embedding fails for any reason, returns the input
    unchanged — dedup is a nice-to-have, not worth failing the request over.
    """
    if len(articles) < 2:
        return articles
    try:
        from sentence_transformers import util
        from analysis.framing import get_model

        model = get_model()
        # First ~1500 chars is plenty to fingerprint syndicated copy.
        embs = model.encode([a.raw_text[:1500] for a in articles])
        sim = util.cos_sim(embs, embs).numpy()
    except Exception as e:
        log.info("wire-copy dedup skipped (%s)", e)
        return articles

    kept: list[LiveArticle] = []
    kept_idx: list[int] = []
    for i, art in enumerate(articles):
        if any(sim[i, j] >= WIRE_COPY_SIM for j in kept_idx):
            log.info("dropping wire copy: %s", art.source)
            continue
        kept.append(art)
        kept_idx.append(i)
    return kept


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------
def fetch_live_event(
    query: str,
    max_sources: int = 10,
    timespan: str = "7d",
    gdelt_maxrecords: int = 75,
) -> list[LiveArticle]:
    """
    Assemble a comparable multi-source event for `query`.

    Returns a list of LiveArticle (>=2), one per outlet, deduped of wire copy.
    Raises LiveIngestError if fewer than 2 usable sources could be gathered
    (the pipeline needs at least a pair to compare).
    """
    hits = _gdelt_search(query, timespan=timespan, maxrecords=gdelt_maxrecords)
    if not hits:
        raise LiveIngestError(
            f"No recent English-language coverage found for “{query}”. "
            f"Try broader wording or a currently-active story."
        )

    # --- collapse to one candidate per domain, preferring known outlets and
    #     earlier (more central) results GDELT returned. ---
    by_domain: dict[str, dict] = {}
    for h in hits:
        info = lookup(h.get("domain") or h.get("url", ""))
        if info.domain not in by_domain:
            by_domain[info.domain] = {"hit": h, "info": info}

    # Order: registry-known outlets first (so a public reader gets recognizable
    # names and lean labels), then by lean bucket for a tidy left→right spread.
    candidates = sorted(
        by_domain.values(),
        key=lambda c: (c["info"].lean == LEAN_UNKNOWN, lean_rank(c["info"].lean)),
    )

    # --- fetch bodies until we have enough usable sources, keeping names unique ---
    articles: list[LiveArticle] = []
    used_names: set[str] = set()
    for cand in candidates:
        if len(articles) >= max_sources:
            break
        info, hit = cand["info"], cand["hit"]
        body = _extract_body(hit.get("url", ""))
        if len(body) < MIN_ARTICLE_CHARS:
            continue

        # Guarantee a unique `source` label — the pipeline uses it as a dict key.
        name = info.name
        if name in used_names:
            name = f"{name} ({info.domain})"
        used_names.add(name)

        articles.append(LiveArticle(
            source=name,
            url=hit.get("url"),
            raw_text=body,
            domain=info.domain,
            lean=info.lean,
            title=hit.get("title"),
        ))

    articles = _dedup_wire_copy(articles)

    if len(articles) < 2:
        raise LiveIngestError(
            f"Only found {len(articles)} readable source(s) for “{query}” — "
            f"need at least 2 to compare. Many results may be paywalled or "
            f"failed to load. Try a bigger story."
        )
    return articles


if __name__ == "__main__":
    # Manual smoke test:  python -m ingestion.live_loader "your topic here"
    import sys

    logging.basicConfig(level=logging.INFO)
    q = " ".join(sys.argv[1:]) or "artificial intelligence regulation"
    for a in fetch_live_event(q):
        print(f"[{a.lean:>7}] {a.source:<28} {len(a.raw_text):>6} chars  {a.url}")
