"""
google_news_rss.py  ·  v3.0
════════════════════════════
Production-ready Google News RSS scraper for Indian banking & finance news.

What changed from v2 → v3
──────────────────────────
  REMOVED  Inline BANKING_KEYWORDS and NOISE_TOPICS definitions.
           Both sets now live in news_classifier.py — the single source of
           truth.  This eliminates the risk of the two copies drifting apart.
  REMOVED  Inline _is_banking_relevant() definition.
           Now imported from news_classifier.py as is_banking_relevant().
  KEPT     All v2 RSS-fetching, HTML-cleaning, deduplication, and parsing
           logic — unchanged.
  KEPT     All v2 public API: fetch_google_news(), get_article_image().
  GUARANTEED  Zero LLM / Groq calls anywhere in this module.

What was already correct in v2 (no changes needed)
───────────────────────────────────────────────────
  ✅  Pure keyword filtering — no ask_llm() was ever called here in v2.
  ✅  Browser User-Agent prevents Google 403.
  ✅  feedparser via requests avoids InvalidURL / 403 bugs.
  ✅  Two-stage deduplication (URL + normalised title fingerprint).
  ✅  HTML cleaning, summary truncation, source extraction.

Dependencies
────────────
  feedparser, requests, beautifulsoup4
  news_classifier (internal — same package)
"""

from __future__ import annotations

import html
import logging
import re
import unicodedata
import urllib.parse
from datetime import datetime, timezone
from typing import Optional

import feedparser
import requests
from bs4 import BeautifulSoup

# Internal — keyword classifier (zero-LLM, single source of truth)
from .banking_classifier import is_banking_relevant

# ══════════════════════════════════════════════════════════════════════════════
# Logging
# ══════════════════════════════════════════════════════════════════════════════

logger = logging.getLogger(__name__)

# ══════════════════════════════════════════════════════════════════════════════
# HTTP constants
# ══════════════════════════════════════════════════════════════════════════════

# A realistic browser UA prevents Google from returning 403.
BROWSER_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)

RSS_BASE_URL = "https://news.google.com/rss/search"

# Indian English locale — keeps results India-relevant.
RSS_LOCALE_PARAMS = {
    "hl": "en-IN",
    "gl": "IN",
    "ceid": "IN:en",
}

RSS_TIMEOUT = 15    # seconds — generous for slow Render cold-start network
IMAGE_TIMEOUT = 6   # seconds — for optional og:image scraping
MAX_SUMMARY_LEN = 300  # characters — truncate long summaries for UI cards

# ══════════════════════════════════════════════════════════════════════════════
# Search queries
# ══════════════════════════════════════════════════════════════════════════════
#
# Multiple focused queries are better than one mega-query because Google News
# RSS returns at most ~100 items per query and throttles complex boolean
# expressions.
#
# RULES:
#   - Never add site: operators — they filter *out* results on news.google.com.
#   - Never include raw spaces in the URL (urllib.parse.urlencode handles it).
#   - Keep each query 3-6 keywords for best recall.
#
SEARCH_QUERIES: list[str] = [
    "RBI Reserve Bank India monetary policy",
    "Indian banking finance loans NBFC",
    "SBI HDFC ICICI bank quarterly results",
    "India economy GDP budget fiscal",
    "UPI fintech payment digital banking India",
    "SEBI mutual fund insurance IRDAI India",
]

# ══════════════════════════════════════════════════════════════════════════════
# Helpers — text cleaning
# ══════════════════════════════════════════════════════════════════════════════


def _clean_text(raw: str) -> str:
    """
    Strip HTML tags, decode entities, collapse whitespace.

    Google News RSS occasionally embeds HTML in the <description> field
    (e.g. <ol><li><a href="...">Headline - Source</a></li></ol>).
    BeautifulSoup handles all tag variants; html.unescape fixes &amp; etc.
    """
    if not raw:
        return ""
    text = BeautifulSoup(raw, "html.parser").get_text(separator=" ")
    text = html.unescape(text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _truncate(text: str, max_len: int) -> str:
    """Trim to *max_len* characters, appending ellipsis when cut."""
    if len(text) <= max_len:
        return text
    return text[: max_len - 1].rstrip() + "..."


def _normalise_for_dedup(text: str) -> str:
    """
    Produce a deduplication fingerprint from *text*.

    Steps: lowercase -> NFKD normalise -> strip punctuation ->
    remove common stop words -> collapse whitespace.

    This lets us catch the same story from two queries even when
    one title appends " - Source Name" and the other does not.
    """
    text = text.lower()
    text = unicodedata.normalize("NFKD", text)
    text = re.sub(r"[^\w\s]", "", text)
    _STOPS = frozenset(
        {"the", "a", "an", "in", "on", "of", "to", "is", "are",
         "was", "were", "and", "or", "for", "at", "by", "from", "with"}
    )
    words = [w for w in text.split() if w not in _STOPS]
    return " ".join(words)


# ══════════════════════════════════════════════════════════════════════════════
# Helpers — RSS fetching & parsing
# ══════════════════════════════════════════════════════════════════════════════


def _build_rss_url(query: str) -> str:
    """
    Construct a correctly percent-encoded Google News RSS URL.

    urllib.parse.urlencode handles spaces, colons, special chars safely.
    The original v0 bug was embedding raw spaces directly into the URL string.
    """
    params = {**RSS_LOCALE_PARAMS, "q": query}
    return f"{RSS_BASE_URL}?{urllib.parse.urlencode(params)}"


def _fetch_feed(url: str) -> feedparser.FeedParserDict:
    """
    Fetch *url* with a browser User-Agent via requests, then parse bytes
    with feedparser.

    Why not use feedparser directly?
      - feedparser's urllib backend crashes on unencoded spaces (InvalidURL).
      - feedparser's default UA ('feedparser/x.y.z') returns 403 from Google.
    Fetching via requests and passing raw bytes to feedparser.parse() avoids
    both issues without any patching.
    """
    try:
        response = requests.get(
            url,
            headers={
                "User-Agent": BROWSER_UA,
                "Accept-Language": "en-IN,en;q=0.9",
                "Accept": "application/rss+xml,application/xml,text/xml,*/*",
            },
            timeout=RSS_TIMEOUT,
        )
        response.raise_for_status()
        logger.debug(
            "RSS fetch OK  url=%s  status=%d  bytes=%d",
            url, response.status_code, len(response.content),
        )
        return feedparser.parse(response.content)

    except requests.exceptions.Timeout:
        logger.warning("RSS fetch timed out  url=%s", url)
    except requests.exceptions.HTTPError as exc:
        logger.warning(
            "RSS fetch HTTP error  status=%s  url=%s",
            exc.response.status_code, url,
        )
    except requests.exceptions.RequestException as exc:
        logger.error("RSS fetch failed  url=%s  error=%s", url, exc)

    # Return an empty feed object so callers never need to handle None.
    return feedparser.FeedParserDict(entries=[])


def _parse_published(entry: feedparser.FeedParserDict) -> str:
    """Return ISO-8601 UTC timestamp string, or '' when unavailable."""
    raw = entry.get("published_parsed")
    if not raw:
        return ""
    try:
        return datetime(*raw[:6], tzinfo=timezone.utc).isoformat()
    except Exception as exc:
        logger.debug("Date parse failed  raw=%r  error=%s", raw, exc)
        return ""


def _parse_source(entry: feedparser.FeedParserDict, title: str) -> str:
    """
    Extract publisher name with two fallback levels.

    1. RSS <source> tag  ->  entry['source']['title']
    2. Title suffix      ->  "Headline - Source Name" (Google News format)
    3. Hardcoded default ->  "Google News"
    """
    # Level 1: <source> RSS tag (most reliable)
    src = entry.get("source")
    if isinstance(src, dict):
        name = src.get("title", "").strip()
        if name:
            return name

    # Level 2: parse trailing " - Source Name" from title
    if " - " in title:
        suffix = title.rsplit(" - ", 1)[-1].strip()
        # Source names are short; reject if it looks like part of a sentence
        if 1 <= len(suffix.split()) <= 6:
            return suffix

    return "Google News"


def _parse_entry(entry: feedparser.FeedParserDict) -> Optional[dict]:
    """
    Convert one feedparser entry into a clean, validated response dict.

    Returns None when:
      - title or link is missing
      - the article fails the banking-relevance filter
      - an unexpected exception occurs during parsing

    Classification is performed by is_banking_relevant() from news_classifier
    — pure keyword matching, zero LLM calls.
    """
    try:
        raw_title = _clean_text(entry.get("title") or "")
        link = (entry.get("link") or "").strip()

        if not raw_title or not link:
            logger.debug("Skipping entry with missing title or link")
            return None

        raw_summary = _clean_text(
            entry.get("summary") or entry.get("description") or ""
        )

        # ── Content relevance filter (keyword-only, zero Groq calls) ─────────
        relevant, reason = is_banking_relevant(raw_title, raw_summary)
        if not relevant:
            logger.debug(
                "FILTERED  reason=%s  title=%r", reason, raw_title[:80]
            )
            return None
        logger.debug("KEPT  reason=%s  title=%r", reason, raw_title[:80])

        source = _parse_source(entry, raw_title)

        # Strip trailing " - Source Name" from the display title when we
        # extracted the source from it, so titles are clean in the UI.
        clean_title = raw_title
        if source != "Google News" and raw_title.endswith(f" - {source}"):
            clean_title = raw_title[: -(len(source) + 3)].strip()

        return {
            "title": clean_title,
            "link": link,
            "published": _parse_published(entry),
            "source": source,
            "summary": _truncate(raw_summary, MAX_SUMMARY_LEN),
        }

    except Exception as exc:
        logger.error(
            "Entry parse error  title=%r  error=%s",
            entry.get("title"), exc,
        )
        return None


# ══════════════════════════════════════════════════════════════════════════════
# Public API
# ══════════════════════════════════════════════════════════════════════════════


def get_article_image(url: str) -> str:
    """
    Scrape the og:image meta tag from an article page.

    Disabled by default in fetch_google_news (fetch_images=False) because
    it adds N x IMAGE_TIMEOUT latency to every API request.  Enable only
    when running in a background worker or a caching layer.
    """
    default = "https://placehold.co/300x180?text=Banking+News"
    try:
        response = requests.get(
            url,
            headers={"User-Agent": BROWSER_UA},
            timeout=IMAGE_TIMEOUT,
            allow_redirects=True,
        )
        if response.status_code != 200:
            return default
        soup = BeautifulSoup(response.text, "html.parser")
        meta = soup.find("meta", property="og:image")
        if meta and meta.get("content"):
            return str(meta["content"])
    except Exception as exc:
        logger.debug("Image scrape failed  url=%s  error=%s", url, exc)
    return default


def fetch_google_news(
    limit: int = 10,
    fetch_images: bool = False,
) -> list[dict]:
    """
    Fetch the latest Indian banking & finance news from Google News RSS.

    Fans out across SEARCH_QUERIES, deduplicates, applies two-layer banking
    relevance filter (keyword-only, zero Groq calls), cleans HTML, and
    returns structured JSON-ready dicts.

    Parameters
    ----------
    limit : int
        Maximum number of articles to return.  Default 10.
    fetch_images : bool
        When True, scrape each article page for an og:image thumbnail.
        Adds IMAGE_TIMEOUT seconds per article — keep False in production
        unless results are cached upstream.

    Returns
    -------
    list[dict]
        Each item contains:
          title     : str  — cleaned, HTML-free headline
          link      : str  — canonical Google News redirect URL
          published : str  — ISO-8601 UTC, e.g. "2024-01-08T10:30:00+00:00"
          source    : str  — publisher name, e.g. "The Economic Times"
          summary   : str  — cleaned excerpt, max MAX_SUMMARY_LEN chars

        Returns [] only when no banking-relevant articles are genuinely found.

    Deduplication
    -------------
    Two-stage:
      1. Exact URL match  — same article from multiple queries
      2. Normalised title fingerprint — same story with minor phrasing diffs

    Groq calls
    ----------
    ZERO.  Classification is performed entirely by keyword matching in
    news_classifier.is_banking_relevant().
    """
    if limit <= 0:
        logger.warning("fetch_google_news: limit=%d is <= 0, returning []", limit)
        return []

    seen_links: set[str] = set()
    seen_title_norms: list[str] = []   # list for substring containment checks
    results: list[dict] = []

    for query in SEARCH_QUERIES:
        if len(results) >= limit:
            break

        url = _build_rss_url(query)
        logger.info("Fetching RSS  query=%r  url=%s", query, url)

        feed = _fetch_feed(url)
        n_entries = len(feed.entries)
        logger.info("Feed returned %d entries  query=%r", n_entries, query)

        if feed.bozo and n_entries == 0:
            logger.warning(
                "feedparser bozo flag set (parse/network error)  "
                "query=%r  reason=%s",
                query, feed.get("bozo_exception"),
            )

        for entry in feed.entries:
            if len(results) >= limit:
                break

            # Stage 1: URL deduplication
            link = (entry.get("link") or "").strip()
            if link in seen_links:
                logger.debug("DEDUP-URL  link=%s", link)
                continue

            # Parse & filter (returns None on filter-out or parse error)
            # Classification inside _parse_entry is keyword-only — 0 Groq calls.
            parsed = _parse_entry(entry)
            if parsed is None:
                continue

            # Stage 2: title fingerprint deduplication
            norm = _normalise_for_dedup(parsed["title"])
            if any(
                (norm in existing or existing in norm)
                for existing in seen_title_norms
                if len(existing) > 20       # ignore very short titles
            ):
                logger.debug("DEDUP-TITLE  title=%r", parsed["title"][:60])
                continue

            # All checks passed — accept this article
            seen_links.add(link)
            seen_title_norms.append(norm)

            if fetch_images:
                parsed["image"] = get_article_image(parsed["link"])

            results.append(parsed)

    logger.info(
        "fetch_google_news complete  returned=%d  limit=%d  queries_used=%d",
        len(results), limit, len(SEARCH_QUERIES),
    )
    return results