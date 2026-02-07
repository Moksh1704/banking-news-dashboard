import os
import requests
from datetime import datetime, timezone, timedelta

from backend.app.services.banking_classifier import is_banking_content_llm


# Fallback keywords (finance/banking)
KEYWORDS = [
    "bank", "rbi", "finance", "financial", "loan",
    "stock", "market", "interest", "rate",
    "economy", "inflation", "investment",
    "credit", "fund", "profit", "revenue"
]


# Check keyword relevance
def is_banking_by_keyword(text: str) -> bool:
    text = text.lower()

    for word in KEYWORDS:
        if word in text:
            return True

    return False


# Convert ISO time safely
def parse_date(date_str):
    try:
        return datetime.fromisoformat(
            date_str.replace("Z", "+00:00")
        )
    except:
        return None


# Main function
def fetch_youtube_news(limit=5, days_back=5):

    API_KEY = os.getenv("YOUTUBE_API_KEY")

    if not API_KEY:
        print("YouTube API key missing")
        return []

    channels = {
        "Bloomberg": "UCIALMKvObZNtJ6AmdCLP7Lg",
        "CNBC": "UCvJJ_dzjViJCoLf5uKUTwoA",
        "Reuters": "UChqUTb7kYRX8-EiaN3XFrSQ"
    }

    base_url = "https://www.googleapis.com/youtube/v3/search"

    results = []

    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=days_back)

    for source, channel_id in channels.items():

        params = {
            "part": "snippet",
            "channelId": channel_id,
            "maxResults": 10,
            "order": "date",
            "type": "video",
            "key": API_KEY
        }

        try:
            res = requests.get(base_url, params=params, timeout=10)
            data = res.json()

            items = data.get("items", [])

        except Exception as e:
            print(f"YouTube fetch error ({source}):", e)
            continue


        for item in items:

            snippet = item["snippet"]

            title = snippet.get("title", "")
            desc = snippet.get("description", "")

            published = parse_date(
                snippet.get("publishedAt", "")
            )

            if not published:
                continue

            if published < cutoff:
                continue


            text = f"{title} {desc}"

            is_relevant = False


            # 1️⃣ Try LLM first
            try:
                is_relevant = is_banking_content_llm(title, desc)

            except Exception as e:
                print("LLM failed → Using keywords:", e)

                # 2️⃣ Fallback to keywords
                is_relevant = is_banking_by_keyword(text)


            if not is_relevant:
                continue


            video_id = item["id"]["videoId"]

            results.append({
                "title": title,
                "summary": desc,
                "published": published.isoformat(),
                "source": source,
                "url": f"https://www.youtube.com/watch?v={video_id}",
                "thumbnail": snippet["thumbnails"]["medium"]["url"],
                "source_type": "youtube"
            })


    # Sort newest first
    results.sort(
        key=lambda x: x["published"],
        reverse=True
    )


    return results[:limit]
