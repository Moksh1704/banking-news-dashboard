import logging
import os
from dotenv import load_dotenv

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# ===============================
# LOAD ENV FILE (IMPORTANT)
# ===============================

BASE_DIR = os.path.dirname(
    os.path.dirname(
        os.path.dirname(os.path.abspath(__file__))
    )
)

ENV_PATH = os.path.join(BASE_DIR, ".env")

load_dotenv(ENV_PATH)

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


# ===============================
# IMPORT SERVICES
# ===============================

from backend.app.services.google_news_rss import fetch_google_news
from backend.app.services.youtube_news import fetch_youtube_news
from backend.app.services.rbi_scraper import fetch_all_rbi_documents

from backend.app.services.rag_pipeline import RAGPipeline
from backend.app.services.vector_store import VectorStore


# ===============================
# FASTAPI INIT
# ===============================

app = FastAPI(
    title="Banking News Intelligence System",
    description="AI-powered Banking News Aggregation and Analysis Platform",
    version="1.0.0"
)


# ===============================
# CORS (for Streamlit)
# ===============================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ===============================
# RAG INIT
# ===============================

vector_store = VectorStore()
rag = RAGPipeline(vector_store)


# ===============================
# ROOT
# ===============================

@app.get("/")
def root():
    return {
        "status": "Running",
        "message": "Banking News API is live"
    }


# ===============================
# GOOGLE NEWS
# ===============================

@app.get("/news/google")
def get_google_news(limit: int = 10):
    """
    Fetch banking related Google News
    """
    try:
        return fetch_google_news(limit=limit)
    except Exception as e:
        logger.exception("Google News Error")
        return []


# ===============================
# YOUTUBE NEWS
# ===============================

@app.get("/news/youtube")
def get_youtube_news(limit: int = 5):
    """
    Fetch YouTube banking videos
    """
    try:
        return fetch_youtube_news(limit=limit)
    except Exception as e:
        logger.exception("YouTube Error")
        return []


# ===============================
# RBI DOCUMENTS
# ===============================

@app.get("/news/rbi")
def get_rbi_docs(limit: int = 5):
    """
    Fetch RBI PDFs
    """
    try:
        return fetch_all_rbi_documents(limit=limit)
    except Exception as e:
        logger.exception("RBI Error")
        return []


# ===============================
# CHATBOT (RAG)
# ===============================

@app.post("/chat")
def ask_question(query: str):
    """
    Ask questions on RBI documents
    """

    if not query.strip():
        return {
            "answer": "Please enter a valid question.",
            "sources": []
        }

    try:
        result = rag.answer(query)

        return {
            "answer": result.get("answer", ""),
            "sources": result.get("sources", [])
        }

    except Exception as e:
        logger.exception("Chat Error")

        return {
            "answer": "Server error. Please try again later.",
            "sources": []
        }
