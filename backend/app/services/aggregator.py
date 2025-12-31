from backend.app.services.web_news import fetch_web_news
from backend.app.services.youtube_news import fetch_youtube_news
from datetime import datetime
import re


# -----------------------------
# Banking relevance filter
# -----------------------------
BANKING_KEYWORDS = [
    "bank", "banking", "rbi", "loan", "interest",
    "credit", "debit", "npa", "finance", "fintech",
    "deposit", "repo", "emi", "mortgage"
]


def is_banking_related(text: str) -> bool:
    if not text:
        return False
    text = text.lower()
    return any(keyword in text for keyword in BANKING_KEYWORDS)


# -----------------------------
# Date parsing
# -----------------------------
def parse_date(date_str):
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


# -----------------------------
# Text cleaning
# -----------------------------
def clean_text(text, limit=250):
    if not text:
        return ""

    text = re.sub(r"<.*?>", "", text)      # remove HTML
    text = text.replace("&nbsp;", " ")
    return text[:limit] + "..." if len(text) > limit else text


# -----------------------------
# Aggregation
# -----------------------------
def aggregate_news(keyword: str, limit: int = 10):
    web_news = fetch_web_news(keyword, limit)
    youtube_news = fetch_youtube_news(keyword, limit)

    aggregated = []

    # Web news
    for item in web_news:
        combined_text = f"{item.get('title', '')} {item.get('summary', '')}"
        if not is_banking_related(combined_text):
            continue

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
        combined_text = f"{item.get('title', '')} {item.get('description', '')}"
        if not is_banking_related(combined_text):
            continue

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

    # Convert datetime → string
    for item in aggregated:
        if item["published"]:
            item["published"] = item["published"].isoformat()

    return aggregated
