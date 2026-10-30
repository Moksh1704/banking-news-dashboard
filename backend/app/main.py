"""
main.py  ·  v1.0  (verified clean — no changes required)
══════════════════════════════════════════════════════════
FastAPI entry-point for the Banking News Intelligence System.

Groq usage audit (performed during v3 refactor)
────────────────────────────────────────────────
  ask_llm() is NOT called directly in this file.
  Groq is accessed exactly once per user request, inside:
    rag.answer(query)  →  RAGPipeline.answer()  →  ask_llm()

  All news endpoints (GET /news/google, /news/youtube, /news/rbi) call
  zero LLM functions — they return pure scraped/parsed data.

  This file requires NO code changes for the v3 refactor.  It is included
  in the output for completeness and as part of the verified-clean audit.
"""

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
    Fetch banking-related Google News.
    Groq calls: ZERO — classification is keyword-only (news_classifier.py).
    """
    try:
        return fetch_google_news(limit=limit)
    except Exception as e:
        print("Google News Error:", e)
        return []


# ===============================
# YOUTUBE NEWS
# ===============================

@app.get("/news/youtube")
def get_youtube_news(limit: int = 5):
    """
    Fetch YouTube banking videos.
    Groq calls: ZERO.
    """
    try:
        return fetch_youtube_news(limit=limit)
    except Exception as e:
        print("YouTube Error:", e)
        return []


# ===============================
# RBI DOCUMENTS
# ===============================

@app.get("/news/rbi")
def get_rbi_docs(limit: int = 5):
    """
    Fetch RBI PDFs.
    Groq calls: ZERO.
    """
    try:
        return fetch_all_rbi_documents(limit=limit)
    except Exception as e:
        print("RBI Error:", e)
        return []


# ===============================
# CHATBOT (RAG)
# ===============================

@app.post("/chat")
def ask_question(query: str):
    """
    Ask questions on RBI documents using RAG.
    Groq calls: EXACTLY ONE per user query, inside rag.answer().
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
        print("Chat Error:", e)

        return {
            "answer": "Server error. Please try again later.",
            "sources": []
        }