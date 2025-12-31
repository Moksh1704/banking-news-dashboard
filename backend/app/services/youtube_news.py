from googleapiclient.discovery import build
from backend.app.config import YOUTUBE_API_KEY

def fetch_youtube_news(keyword: str, limit: int = 10):
    """
    Fetch banking-related news videos from YouTube.
    """
    if not YOUTUBE_API_KEY:
        return {"error": "YouTube API key not configured"}

    youtube = build("youtube", "v3", developerKey=YOUTUBE_API_KEY)

    request = youtube.search().list(
        q=keyword,
        part="snippet",
        type="video",
        maxResults=limit,
        order="date"
    )

    response = request.execute()

    videos = []

    for item in response.get("items", []):
        video_id = item["id"]["videoId"]
        snippet = item["snippet"]

        videos.append({
            "title": snippet["title"],
            "channel": snippet["channelTitle"],
            "published": snippet["publishedAt"],
            "description": snippet["description"],
            "video_url": f"https://www.youtube.com/watch?v={video_id}",
            "thumbnail": snippet["thumbnails"]["high"]["url"]
        })

    return videos
