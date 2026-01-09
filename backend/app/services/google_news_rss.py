import feedparser
from urllib.parse import quote
import re
from html import unescape


def clean_html(text: str) -> str:
    if not text:
        return ""
    text = unescape(text)
    text = re.sub(r"<.*?>", "", text)
    return text.strip()


def fetch_google_news(
    query="banking OR RBI OR NBFC OR bank regulation",
    limit=15
):
    encoded_query = quote(query)
    rss_url = (
        f"https://news.google.com/rss/search?"
        f"q={encoded_query}&hl=en-IN&gl=IN&ceid=IN:en"
    )

    feed = feedparser.parse(rss_url)
    articles = []

    for entry in feed.entries[:limit]:
        articles.append({
            "title": clean_html(entry.get("title", "")),
            "summary": clean_html(entry.get("summary", "")),
            "published": entry.get("published", ""),
            "source": entry.get("source", {}).get("title", "Google News"),
            "url": entry.get("url", ""),
            "source_type": "google_news"
        })

    return articles
