from backend.app.services.rbi_ingest import ingest_rbi_into_vector_store

store = ingest_rbi_into_vector_store(limit=5)

results = store.search("RBI monetary policy")

print("Retrieved chunks:")
print("=" * 60)
for r in results:
    print(r[:400])
    print("-" * 60)
