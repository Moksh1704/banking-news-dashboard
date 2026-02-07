import feedparser
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timezone


DEFAULT_IMAGE = "https://via.placeholder.com/300x180.png?text=Banking+News"


def get_article_image(url: str) -> str:
    """
    Extract og:image from article page
    """
    try:
        headers = {
            "User-Agent": "Mozilla/5.0"
        }

        res = requests.get(url, timeout=6, headers=headers)

        if res.status_code != 200:
            return DEFAULT_IMAGE

        soup = BeautifulSoup(res.text, "html.parser")

        meta = soup.find("meta", property="og:image")

        if meta and meta.get("content"):
            return meta["content"]

        return DEFAULT_IMAGE

    except Exception:
        return DEFAULT_IMAGE


def fetch_google_news(limit: int = 10):
    """
    Fetch banking related Google News with images
    """

    query = "banking OR RBI OR finance OR loans OR interest rates site:news.google.com"

    rss_url = f"https://news.google.com/rss/search?q={query}&hl=en-IN&gl=IN&ceid=IN:en"

    feed = feedparser.parse(rss_url)

    results = []

    for entry in feed.entries[:limit]:

        published = None

        try:
            published = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
        except Exception:
            published = None

        image = get_article_image(entry.link)

        results.append({
            "title": entry.title,
            "link": entry.link,
            "source": entry.source.title if "source" in entry else "Google News",
            "published": published.isoformat() if published else "",
            "image": image,
            "type": "google"
        })

    return results
