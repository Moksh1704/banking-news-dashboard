from backend.app.services.pdf_parser import extract_text_from_pdf_url
from backend.app.services.text_cleaner import clean_text
from backend.app.services.text_chunker import chunk_text
from backend.app.services.vector_store import VectorStore
from backend.app.services.rag_pipeline import RAGPipeline

pdf_url = "https://www.rbi.org.in/commonman/Upload/English/PressRelease/PDFs/PR1791.pdf"

# Step 1: Prepare knowledge base
raw = extract_text_from_pdf_url(pdf_url)
cleaned = clean_text(raw)
chunks = chunk_text(cleaned)

store = VectorStore()
store.add_documents(chunks)

# Step 2: Ask question via RAG
rag = RAGPipeline(store)

print("Calling RAG...")
answer = rag.answer("What action did RBI take against Valuecorp?")

print("LLM returned:")
print(answer)
