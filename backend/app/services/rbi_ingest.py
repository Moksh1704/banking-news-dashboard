import re
import unicodedata
from typing import Any, Dict, Iterable, List

from backend.app.services.rbi_scraper import fetch_all_rbi_documents
from backend.app.services.text_chunker import chunk_text
from backend.app.services.text_cleaner import clean_text
from backend.app.services.vector_store import VectorStore


def _normalized_chunk_key(text: str) -> str:
    normalized = unicodedata.normalize("NFKC", text).casefold()
    return re.sub(r"\s+", " ", normalized).strip()


def prepare_rbi_chunks(
    documents: Iterable[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Convert RBI documents into text chunks with source metadata."""
    chunks: List[Dict[str, Any]] = []
    for document in documents:
        text = clean_text(document.get("content", ""))
        seen_chunks = set()
        for chunk in chunk_text(text):
            key = _normalized_chunk_key(chunk)
            if not key or key in seen_chunks:
                continue
            seen_chunks.add(key)
            chunks.append(
                {
                    "text": chunk,
                    "metadata": {
                        "title": document.get("title"),
                        "url": document.get("url"),
                        "source": document.get("source", "RBI"),
                        "category": document.get("category"),
                        "type": "rbi",
                    },
                }
            )
    return chunks


def ingest_rbi_into_vector_store(limit: int = 10) -> VectorStore:
    """
    Full RBI ingestion pipeline:
    PDF → text → metadata-preserving chunks → embeddings → FAISS
    """

    vector_store = VectorStore()
    documents = fetch_all_rbi_documents(limit=limit)
    vector_store.add_documents(prepare_rbi_chunks(documents))
    return vector_store
