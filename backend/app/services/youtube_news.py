import os
import requests
from dotenv import load_dotenv
from typing import List, Dict

from backend.app.services.banking_classifier import is_banking_content

load_dotenv()

YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")

# Trusted news channels ONLY
CHANNELS = {
    "Bloomberg": "UCIALMKvObZNtJ6AmdCLP7Lg",
    "Reuters": "UChqUTb7kYRX8-EiaN3XFrSQ",
    "CNBC": "UCvJJ_dzjViJCoLf5uKUTwoA",
    "CNBC-TV18": "UCz4b1k5J8zZ6YJk9qZf8ZVQ"
}


def fetch_youtube_news(limit: int = 10) -> List[Dict]:
    if not YOUTUBE_API_KEY:
        print("YouTube API key missing")
        return []

    collected = []

    for source, channel_id in CHANNELS.items():
        url = "https://www.googleapis.com/youtube/v3/search"

        params = {
            "key": YOUTUBE_API_KEY,
            "channelId": channel_id,
            "part": "snippet",
            "order": "date",
            "maxResults": 10,
            "type": "video"
        }

        try:
            response = requests.get(url, params=params, timeout=10)
            data = response.json()
            items = data.get("items", [])

            for item in items:
                snippet = item.get("snippet", {})
                video_id = item.get("id", {}).get("videoId")

                if not video_id:
                    continue

                title = snippet.get("title", "")
                description = snippet.get("description", "")

                # LLM FILTER
                if not is_banking_content(title, description):
                    continue

                collected.append({
                    "title": title,
                    "summary": description,
                    "published": snippet.get("publishedAt"),
                    "source": source,
                    "url": f"https://www.youtube.com/watch?v={video_id}",
                    "thumbnail": snippet.get("thumbnails", {}).get("medium", {}).get("url"),
                    "source_type": "youtube"
                })

        except Exception as e:
            print(f"YouTube fetch error ({source}):", e)

    collected.sort(key=lambda x: x.get("published", ""), reverse=True)
    return collected[:limit]
