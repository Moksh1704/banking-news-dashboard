from backend.app.services.rbi_scraper import fetch_rbi_press_releases

data = fetch_rbi_press_releases(limit=2)

print("Items fetched:", len(data))

for item in data:
    print("=" * 60)
    print(item["title"])
    print(item["published"])
    print(item["content"][:500])
