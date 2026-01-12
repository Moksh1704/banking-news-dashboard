import os
import requests
from typing import List, Dict
from dotenv import load_dotenv

from backend.app.services.llm_client import llm_call

load_dotenv()

YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")

CHANNELS = {
    "Bloomberg": "UCIALMKvObZNtJ6AmdCLP7Lg",
    "Reuters": "UChqUTb7kYRX8-EiaN3XFrSQ",
    "Financial Times": "UC5G6r7n7Q3PZ2kz5mBf9rBw",
    "CNBC": "UCvJJ_dzjViJCoLf5uKUTwoA",
    "CNBC-TV18": "UCmRB5x0G8p4V9zKkZl4yqWw"
}


def summarize_with_llm(title: str, description: str) -> str | None:
    prompt = f"""
Summarize the following BANKING or FINANCIAL news in SIMPLE terms.

Rules:
- 2–3 sentences
- No technical jargon
- Explain what happened and why it matters
- If the content is NOT about banking or finance, respond with: NOT_RELEVANT

Title: {title}
Description: {description}
"""

    response = llm_call(prompt, temperature=0.3).strip()

    if "NOT_RELEVANT" in response.upper():
        return None

    # Basic sanity check
    if len(response) < 30:
        return None

    return response

    prompt = f"""
You are a classifier for a banking news dashboard.

You MUST respond in EXACTLY ONE of the following formats:

FORMAT 1 (if banking-related):
SUMMARY: <2-3 simple sentences explaining the news>

FORMAT 2 (if NOT banking-related):
NOT_RELEVANT

Rules:
- Do NOT explain your reasoning
- Do NOT repeat the question
- Do NOT include the word "Task"
- Follow the format EXACTLY

Content:
Title: {title}
Description: {description}
"""

    response = llm_call(prompt, temperature=0.0).strip()

    response_upper = response.upper()

    # ✅ HARD FILTER
    if response_upper.startswith("NOT_RELEVANT"):
        return None

    if not response_upper.startswith("SUMMARY:"):
        # Garbage output → reject
        return None

    # ✅ Clean summary
    summary = response[len("SUMMARY:"):].strip()

    # Safety: very short summaries are useless
    if len(summary) < 30:
        return None

    return summary


def fetch_youtube_news(limit: int = 5) -> List[Dict]:
    if not YOUTUBE_API_KEY:
        print("❌ YOUTUBE_API_KEY missing")
        return []

    results: List[Dict] = []

    for source, channel_id in CHANNELS.items():
        url = "https://www.googleapis.com/youtube/v3/search"

        params = {
            "key": YOUTUBE_API_KEY,
            "channelId": channel_id,
            "part": "snippet",
            "order": "date",
            "type": "video",
            "maxResults": 2
        }

        try:
            response = requests.get(url, params=params, timeout=10)
            if response.status_code != 200:
                continue

            items = response.json().get("items", [])

            for item in items:
                snippet = item.get("snippet", {})
                video_id = item.get("id", {}).get("videoId")
                if not video_id:
                    continue

                title = snippet.get("title", "")
                description = snippet.get("description", "")
                
                summary = summarize_with_llm(title, description)
                if not summary:
                    continue

                results.append({
                    "title": title,
                    "summary": summary,
                    "published": snippet.get("publishedAt"),
                    "source": source,
                    "url": f"https://www.youtube.com/watch?v={video_id}",
                    "thumbnail": snippet.get("thumbnails", {})
                                    .get("medium", {})
                                    .get("url"),
                    "source_type": "youtube"
                })

        except Exception as e:
            print(f"[YouTube][{source}] Error:", e)
            continue

    results.sort(
        key=lambda x: x.get("published") or "",
        reverse=True
    )

    return results[:limit]
