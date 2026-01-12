from fastapi import FastAPI
from pydantic import BaseModel

# =========================
# RAG + Vector Store
# =========================
from backend.app.services.vector_store import VectorStore
from backend.app.services.rag_pipeline import RAGPipeline

# RBI ingestion
from backend.app.services.pdf_parser import extract_text_from_pdf_url
from backend.app.services.text_cleaner import clean_text
from backend.app.services.text_chunker import chunk_text

# News sources
from backend.app.services.google_news_rss import fetch_google_news
from backend.app.services.youtube_news import fetch_youtube_news


# =========================
# FASTAPI APP
# =========================
app = FastAPI(
    title="Banking News Intelligence API",
    description="Backend API for banking news aggregation and analysis",
    version="1.0"
)


# =========================
# GLOBAL OBJECTS
# =========================
store = VectorStore()
rag = RAGPipeline(store)

# ---- RBI SOURCE ----
RBI_PDF_URL = (
    "https://www.rbi.org.in/commonman/Upload/English/"
    "PressRelease/PDFs/PR1791.pdf"
)

# Toggle RBI ingestion (VERY IMPORTANT FOR DEV)
LOAD_RBI_ON_STARTUP = False


# =========================
# STARTUP EVENT (FIXED)
# =========================
@app.on_event("startup")
def load_rbi_data():
    """
    Load RBI PDF safely on startup.
    This will NOT crash the server if RBI site is slow.
    """
    if not LOAD_RBI_ON_STARTUP:
        print("ℹ️ RBI ingestion skipped on startup")
        return

    try:
        print("⏳ Loading RBI PDF...")
        raw_text = extract_text_from_pdf_url(RBI_PDF_URL)
        cleaned_text = clean_text(raw_text)
        chunks = chunk_text(cleaned_text)
        store.add_documents(chunks)
        print("✅ RBI data loaded successfully")
    except Exception as e:
        print("⚠️ RBI ingestion failed:", e)


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
        "rbi_loaded": LOAD_RBI_ON_STARTUP
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
    return fetch_google_news(limit=limit)


# =========================
# YOUTUBE NEWS ENDPOINT
# =========================
@app.get("/news/youtube")
def youtube_news(limit: int = 10):
    """
    Fetch banking-related YouTube news
    (LLM relevance + summarization handled inside youtube_news)
    """
    return fetch_youtube_news(limit=limit)
