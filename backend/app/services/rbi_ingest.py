from backend.app.services.rbi_scraper import fetch_all_rbi_documents
from backend.app.services.text_chunker import chunk_text
from backend.app.services.vector_store import VectorStore

def ingest_rbi_into_vector_store(limit: int = 10) -> VectorStore:
    """
    Full RBI ingestion pipeline:
    PDF → text → chunks → embeddings → FAISS
    """

    vector_store = VectorStore()
    documents = fetch_all_rbi_documents(limit=limit)

    all_chunks = []

    for doc in documents:
        chunks = chunk_text(doc["content"])
        all_chunks.extend(chunks)

    vector_store.add_documents(all_chunks)
    return vector_store
