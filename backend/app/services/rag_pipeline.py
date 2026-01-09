from backend.app.services.llm_service import ask_ollama


class RAGPipeline:
    def __init__(self, vector_store):
        self.vector_store = vector_store

    def answer(self, question: str) -> str:
        retrieved_chunks = self.vector_store.search(question, top_k=2)

        context = "\n\n".join(retrieved_chunks)

        prompt = f"""
You are a banking assistant.
Answer the question ONLY using the context below.
Be concise (max 3 sentences).

Context:
{context}

Question:
{question}

Answer:
"""

        return ask_ollama(prompt)
