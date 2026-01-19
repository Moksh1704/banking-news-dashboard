# backend/app/services/rag_pipeline.py

from backend.app.services.llm_service import ask_gemini
from backend.app.services.vector_store import VectorStore


class RAGPipeline:
    def __init__(self, vector_store: VectorStore):
        self.vector_store = vector_store

    def answer(self, query: str) -> str:
        docs = self.vector_store.search(query, k=4)

        if not docs:
            return "No relevant RBI or banking documents found."

        context_blocks = []
        citations = []

        for i, doc in enumerate(docs, start=1):
            context_blocks.append(f"[Source {i}]\n{doc['text']}")
            citations.append(
                f"[{i}] {doc.get('source', 'RBI Document')} | Page {doc.get('page', 'N/A')}"
            )

        context = "\n\n".join(context_blocks)

        prompt = f"""
You are a banking expert assistant.

Answer the question using ONLY the context below.
If unsure, say so clearly.

Context:
{context}

Question:
{query}

Answer in clear, simple language.
"""

        answer = ask_gemini(prompt)

        return f"""
{answer}

Sources:
{chr(10).join(citations)}
"""
