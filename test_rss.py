import feedparser
from backend.app.services.rss_ingestor import fetch_rss_items

rss_url = "https://feeds.reuters.com/reuters/businessNews"

feed = feedparser.parse(rss_url)

print("Feed status:", feed.bozo)
print("Feed title:", feed.feed.get("title"))
print("Total entries found:", len(feed.entries))

items = fetch_rss_items(rss_url, limit=3)

print("Items returned by function:", len(items))

for item in items:
    print("=" * 50)
    print(item["title"])
    print(item["link"])
