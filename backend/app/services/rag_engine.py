from typing import List
from backend.app.services.vector_store import VectorStore

class RAGEngine:
    def __init__(self, vector_store: VectorStore):
        self.vector_store = vector_store

    def build_prompt(self, context_chunks: List[str], question: str) -> str:
        context = "\n\n".join(context_chunks)

        prompt = f"""
You are a banking domain assistant.
Answer ONLY using the RBI and banking context below.
If the answer is not present, say "Information not available in RBI data".

Context:
{context}

Question:
{question}

Answer in simple, professional language.
"""
        return prompt

    def answer(self, question: str) -> str:
        retrieved_docs = self.vector_store.search(question, k=5)

        if not retrieved_docs:
            return "No relevant RBI information found."

        prompt = self.build_prompt(retrieved_docs, question)

        # 🔹 OFFLINE MODE (safe fallback)
        # Replace this with LLM call later
        return retrieved_docs[0][:600]
