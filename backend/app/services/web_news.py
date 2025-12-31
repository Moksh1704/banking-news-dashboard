import feedparser


def fetch_web_news(keyword: str, limit: int = 10):
    """
    Fetch banking-related news from Google News RSS.
    """
    query = keyword.replace(" ", "+")
    rss_url = f"https://news.google.com/rss/search?q={query}"

    feed = feedparser.parse(rss_url)

    news_items = []

    for entry in feed.entries[:limit]:
        news_items.append({
            "title": entry.title,
            "source": entry.source.title if hasattr(entry, "source") else "Google News",
            "published": entry.published if hasattr(entry, "published") else "",
            "summary": entry.summary,
            "link": entry.link
        })

    return news_items
