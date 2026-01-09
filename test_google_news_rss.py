from backend.app.services.google_news_rss import fetch_google_news

articles = fetch_google_news(limit=5)

print(f"Articles found: {len(articles)}")
print("=" * 50)

for a in articles:
    print(a["title"])
    print(a["source"])
    print(a["published"])
    print(a["url"])
    print("-" * 50)
