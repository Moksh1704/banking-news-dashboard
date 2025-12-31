from backend.app.services.web_news import fetch_web_news
from backend.app.services.youtube_news import fetch_youtube_news
from datetime import datetime
import re

def parse_date(date_str):
    """
    Convert different date formats to datetime.
    """
    if not date_str:
        return None

    formats = [
        "%a, %d %b %Y %H:%M:%S %Z",  # Google News
        "%Y-%m-%dT%H:%M:%SZ"         # YouTube
    ]

    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue

    return None


def clean_text(text, limit=200):
    """
    Remove HTML tags and trim text.
    """
    if not text:
        return ""

    # Remove HTML tags
    text = re.sub(r"<.*?>", "", text)

    # Replace HTML entities
    text = text.replace("&nbsp;", " ")

    # Trim text
    return text[:limit] + "..." if len(text) > limit else text


def aggregate_news(keyword: str, limit: int = 10):
    web_news = fetch_web_news(keyword, limit)
    youtube_news = fetch_youtube_news(keyword, limit)

    aggregated = []

    # Web news
    for item in web_news:
        published_dt = parse_date(item.get("published"))

        aggregated.append({
            "source_type": "web",
            "title": item.get("title"),
            "source": item.get("source"),
            "published": published_dt,
            "summary": clean_text(item.get("summary")),
            "link": item.get("link")
        })

    # YouTube news
    for item in youtube_news:
        published_dt = parse_date(item.get("published"))

        aggregated.append({
            "source_type": "youtube",
            "title": item.get("title"),
            "source": item.get("channel"),
            "published": published_dt,
            "summary": clean_text(item.get("description")),
            "link": item.get("video_url"),
            "thumbnail": item.get("thumbnail")
        })

    # Sort latest first
    aggregated.sort(
        key=lambda x: x["published"] or datetime.min,
        reverse=True
    )

    # Convert datetime back to string
    for item in aggregated:
        if item["published"]:
            item["published"] = item["published"].isoformat()

    return aggregated
