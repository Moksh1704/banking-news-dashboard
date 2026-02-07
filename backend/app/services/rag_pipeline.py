import logging
from typing import Any, Dict, List

from backend.app.services.llm_service import ask_gemini
from backend.app.services.rbi_scraper import fetch_all_rbi_documents
from backend.app.services.text_chunker import chunk_text
from backend.app.services.text_cleaner import clean_text
from backend.app.services.vector_store import VectorStore

logger = logging.getLogger(__name__)


class RAGPipeline:
    def __init__(
        self,
        vector_store: VectorStore,
        top_k: int = 3,
        auto_ingest: bool = True,
        ingest_limit: int = 10,
        fallback_char_limit: int = 800,
    ):
        self.vector_store = vector_store
        self.top_k = top_k
        self.auto_ingest = auto_ingest
        self.ingest_limit = ingest_limit
        self._ingestion_attempted = False
        self.fallback_char_limit = fallback_char_limit

    def _ensure_index(self) -> bool:
        if self.vector_store.is_ready():
            return True

        if self.vector_store.load():
            return True

        if not self.auto_ingest or self._ingestion_attempted:
            return False

        self._ingestion_attempted = True
        logger.info("No existing index found. Building RBI embeddings...")

        try:
            documents = fetch_all_rbi_documents(limit=self.ingest_limit)
            all_chunks: List[Dict[str, Any]] = []

            for doc in documents:
                raw_text = doc.get("content", "")
                cleaned_text = clean_text(raw_text)
                chunks = chunk_text(cleaned_text)

                for chunk in chunks:
                    all_chunks.append(
                        {
                            "text": chunk,
                            "metadata": {
                                "title": doc.get("title"),
                                "url": doc.get("url"),
                                "source": doc.get("source", "RBI"),
                            },
                        }
                    )

            if not all_chunks:
                logger.warning("No chunks generated from RBI documents.")
                return False

            self.vector_store.add_documents(all_chunks)
            self.vector_store.save()
            return self.vector_store.is_ready()
        except Exception:
            logger.exception("Failed to build RBI embeddings.")
            return False

    def answer(self, query: str) -> Dict[str, Any]:
        try:
            if not query.strip():
                return {"answer": "Please enter a valid question.", "sources": []}

            if not self._ensure_index():
                return {
                    "answer": "RBI index is not ready yet. Please try again later.",
                    "sources": [],
                }

            # 1. Search relevant docs
            docs = self.vector_store.search(query, top_k=self.top_k)

            if not docs:
                return {
                    "answer": "No relevant RBI documents found for this query.",
                    "sources": [],
                }

            # 2. Build context
            context_blocks = []
            for i, doc in enumerate(docs, 1):
                context_blocks.append(f"[Source {i}]\n{doc['text']}")

            context = "\n\n".join(context_blocks)

            # 3. Prompt
            prompt = f"""
You are a banking assistant.
Answer using the RBI context below.
If the answer is not present, say "Information not available in RBI data".

Context:
{context}

Question:
{query}

Answer clearly and professionally.
"""

            # 4. Ask LLM
            response = ask_gemini(prompt)

            if not response:
                # Fallback: return the most relevant chunk(s) when Gemini is unavailable
                fallback_text = docs[0]["text"][: self.fallback_char_limit]
                return {
                    "answer": (
                        "AI quota is currently unavailable. "
                        "Here is the most relevant RBI excerpt:\n\n"
                        f"{fallback_text}"
                    ),
                    "sources": [
                        {
                            "title": docs[0].get("metadata", {}).get("title"),
                            "url": docs[0].get("metadata", {}).get("url"),
                            "source": docs[0].get("metadata", {}).get("source", "RBI"),
                            "page": docs[0].get("metadata", {}).get("page"),
                            "score": docs[0].get("score"),
                        }
                    ],
                }

            sources = []
            for doc in docs:
                metadata = doc.get("metadata", {})
                sources.append(
                    {
                        "title": metadata.get("title"),
                        "url": metadata.get("url"),
                        "source": metadata.get("source", "RBI"),
                        "page": metadata.get("page"),
                        "score": doc.get("score"),
                    }
                )

            return {"answer": response, "sources": sources}
        except Exception:
            logger.exception("RAG pipeline failed.")
            return {
                "answer": "Sorry, the chatbot service is currently unavailable.",
                "sources": [],
            }
