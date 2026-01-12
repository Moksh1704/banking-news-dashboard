from backend.app.services.rbi_scraper import fetch_all_rbi_documents

docs = fetch_all_rbi_documents(limit=5)

print(f"Total RBI docs fetched: {len(docs)}")

for d in docs:
    print("=" * 80)
    print(d["title"])
    print(d["content"][:800])
