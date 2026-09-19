"""
Source registry — maps a news domain to a human display name and a coarse
political lean, for the live-ingestion path (Phase 1).

Why this exists: BASIL handed us clean source labels ('fox', 'nyt', 'huffpost')
and everyone knew their lean implicitly. Live GDELT results arrive as bare
domains ('foxnews.com', 'apnews.com', 'some-blog.example'), so before the
analysis is meaningful to a public audience we need to (a) turn the domain
into a readable outlet name and (b) attach a lean bucket so the UI can group
left / center / right instead of showing an undifferentiated wall of outlets.

The lean buckets are deliberately COARSE and are NOT a claim of ground truth.
They're drawn from the broad consensus of public media-bias trackers
(AllSides / Media Bias Fact Check style) and are only meant to help a reader
orient — "these three lean left, those two lean right" — not to certify any
outlet's politics. Unlisted domains come back as lean='unknown' rather than
being dropped, so niche/local outlets still show up (just ungrouped).

To extend: add a row to LEAN_BY_DOMAIN. Keep keys as the bare registrable
domain, lowercase, no 'www.'.
"""
from __future__ import annotations

from dataclasses import dataclass

# Coarse lean buckets. 'center' includes wire services and outlets broadly
# rated center/least-biased; 'unknown' is the honest default for anything
# not in the table.
LEAN_LEFT = "left"
LEAN_CENTER = "center"
LEAN_RIGHT = "right"
LEAN_UNKNOWN = "unknown"

# domain -> (display name, lean). Lowercase, registrable domain only.
# Intentionally a modest, high-confidence set — better to label 40 outlets
# most people will actually encounter than to guess at hundreds.
SOURCE_REGISTRY: dict[str, tuple[str, str]] = {
    # --- wire services / broadly center ---
    "apnews.com": ("Associated Press", LEAN_CENTER),
    "reuters.com": ("Reuters", LEAN_CENTER),
    "bbc.com": ("BBC", LEAN_CENTER),
    "bbc.co.uk": ("BBC", LEAN_CENTER),
    "npr.org": ("NPR", LEAN_CENTER),
    "pbs.org": ("PBS", LEAN_CENTER),
    "csmonitor.com": ("Christian Science Monitor", LEAN_CENTER),
    "thehill.com": ("The Hill", LEAN_CENTER),
    "axios.com": ("Axios", LEAN_CENTER),
    "usatoday.com": ("USA Today", LEAN_CENTER),
    "bloomberg.com": ("Bloomberg", LEAN_CENTER),
    "wsj.com": ("Wall Street Journal", LEAN_CENTER),
    "forbes.com": ("Forbes", LEAN_CENTER),
    "marketwatch.com": ("MarketWatch", LEAN_CENTER),
    "newsweek.com": ("Newsweek", LEAN_CENTER),
    "aljazeera.com": ("Al Jazeera", LEAN_CENTER),
    # --- lean left ---
    "nytimes.com": ("New York Times", LEAN_LEFT),
    "washingtonpost.com": ("Washington Post", LEAN_LEFT),
    "cnn.com": ("CNN", LEAN_LEFT),
    "msnbc.com": ("MSNBC", LEAN_LEFT),
    "nbcnews.com": ("NBC News", LEAN_LEFT),
    "abcnews.go.com": ("ABC News", LEAN_LEFT),
    "cbsnews.com": ("CBS News", LEAN_LEFT),
    "theguardian.com": ("The Guardian", LEAN_LEFT),
    "huffpost.com": ("HuffPost", LEAN_LEFT),
    "huffingtonpost.com": ("HuffPost", LEAN_LEFT),
    "vox.com": ("Vox", LEAN_LEFT),
    "slate.com": ("Slate", LEAN_LEFT),
    "motherjones.com": ("Mother Jones", LEAN_LEFT),
    "theatlantic.com": ("The Atlantic", LEAN_LEFT),
    "newyorker.com": ("The New Yorker", LEAN_LEFT),
    "politico.com": ("Politico", LEAN_LEFT),
    "time.com": ("TIME", LEAN_LEFT),
    "businessinsider.com": ("Business Insider", LEAN_LEFT),
    "salon.com": ("Salon", LEAN_LEFT),
    "thedailybeast.com": ("The Daily Beast", LEAN_LEFT),
    # --- lean right ---
    "foxnews.com": ("Fox News", LEAN_RIGHT),
    "nypost.com": ("New York Post", LEAN_RIGHT),
    "washingtontimes.com": ("Washington Times", LEAN_RIGHT),
    "washingtonexaminer.com": ("Washington Examiner", LEAN_RIGHT),
    "breitbart.com": ("Breitbart", LEAN_RIGHT),
    "dailywire.com": ("The Daily Wire", LEAN_RIGHT),
    "dailycaller.com": ("The Daily Caller", LEAN_RIGHT),
    "nationalreview.com": ("National Review", LEAN_RIGHT),
    "theblaze.com": ("The Blaze", LEAN_RIGHT),
    "newsmax.com": ("Newsmax", LEAN_RIGHT),
    "foxbusiness.com": ("Fox Business", LEAN_RIGHT),
    "thefederalist.com": ("The Federalist", LEAN_RIGHT),
    "nydailynews.com": ("New York Daily News", LEAN_LEFT),
}

# Lean sort order for stable left→center→right grouping in the UI.
LEAN_ORDER = {LEAN_LEFT: 0, LEAN_CENTER: 1, LEAN_RIGHT: 2, LEAN_UNKNOWN: 3}


@dataclass
class SourceInfo:
    domain: str      # normalized registrable domain, e.g. 'foxnews.com'
    name: str        # display name, e.g. 'Fox News'
    lean: str        # one of LEAN_* buckets


def normalize_domain(domain_or_url: str) -> str:
    """
    Reduce a domain or URL to a bare, lowercase registrable domain:
    'https://www.FoxNews.com/politics/x' -> 'foxnews.com'.

    Deliberately simple string surgery (no tldextract dependency): strip
    scheme, path, leading 'www.'/'m.'/'amp.' hosts, and lowercase. Good
    enough for the mainstream outlets in the registry; unlisted hosts just
    fall through to lean='unknown', which is a safe default.
    """
    d = (domain_or_url or "").strip().lower()
    if "://" in d:
        d = d.split("://", 1)[1]
    d = d.split("/", 1)[0]        # drop path
    d = d.split("?", 1)[0]
    d = d.split(":", 1)[0]        # drop port
    for prefix in ("www.", "m.", "amp.", "www1.", "edition."):
        if d.startswith(prefix):
            d = d[len(prefix):]
    return d


def _prettify_unknown(domain: str) -> str:
    """
    Turn an unregistered domain into a passable display name:
    'some-local-paper.com' -> 'Some Local Paper'. Never as good as a curated
    name, but better than showing a bare domain in the UI.
    """
    core = domain.rsplit(".", 1)[0] if "." in domain else domain
    core = core.replace("-", " ").replace("_", " ")
    return " ".join(w.capitalize() for w in core.split()) or domain


def lookup(domain_or_url: str) -> SourceInfo:
    """Resolve any domain/URL to a SourceInfo, always returning something."""
    domain = normalize_domain(domain_or_url)
    if domain in SOURCE_REGISTRY:
        name, lean = SOURCE_REGISTRY[domain]
        return SourceInfo(domain=domain, name=name, lean=lean)
    return SourceInfo(domain=domain, name=_prettify_unknown(domain), lean=LEAN_UNKNOWN)


def lean_rank(lean: str) -> int:
    """Sort key so callers can order sources left → center → right → unknown."""
    return LEAN_ORDER.get(lean, LEAN_ORDER[LEAN_UNKNOWN])
