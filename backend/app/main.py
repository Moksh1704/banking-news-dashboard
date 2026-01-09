from fastapi import FastAPI
from pydantic import BaseModel

# RAG + Vector Store
from backend.app.services.vector_store import VectorStore
from backend.app.services.rag_pipeline import RAGPipeline

# RBI ingestion
from backend.app.services.pdf_parser import extract_text_from_pdf_url
from backend.app.services.text_cleaner import clean_text
from backend.app.services.text_chunker import chunk_text

# Google News
from backend.app.services.google_news_rss import fetch_google_news


# =========================
# FASTAPI APP
# =========================
app = FastAPI(
    title="Banking News Intelligence API",
    description="RAG-based backend for banking news and regulatory intelligence",
    version="1.0"
)

# =========================
# LOAD DATA ON STARTUP
# =========================
store = VectorStore()

# ---- RBI SOURCE (AUTHORITATIVE) ----
RBI_PDF_URL = (
    "https://www.rbi.org.in/commonman/Upload/English/"
    "PressRelease/PDFs/PR1791.pdf"
)

raw_text = extract_text_from_pdf_url(RBI_PDF_URL)
cleaned_text = clean_text(raw_text)
chunks = chunk_text(cleaned_text)

store.add_documents(chunks)

# Initialize RAG
rag = RAGPipeline(store)


# =========================
# REQUEST MODELS
# =========================
class QueryRequest(BaseModel):
    question: str


# =========================
# HEALTH CHECK
# =========================
@app.get("/")
def health_check():
    return {
        "status": "Banking News Intelligence API running",
        "sources_loaded": ["RBI PDF"]
    }


# =========================
# CHATBOT (RAG)
# =========================
@app.post("/ask")
def ask_question(request: QueryRequest):
    """
    Answer banking-related questions using RAG
    """
    answer = rag.answer(request.question)
    return {
        "question": request.question,
        "answer": answer
    }


# =========================
# GOOGLE NEWS ENDPOINT
# =========================
@app.get("/news/google")
def get_google_news(limit: int = 10):
    """
    Fetch latest banking-related news from Google News RSS
    """
    articles = fetch_google_news(limit=limit)
    return articles
