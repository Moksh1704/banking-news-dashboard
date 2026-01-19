# backend/app/main.py

from fastapi import FastAPI
from backend.app.services.youtube_news import fetch_youtube_news

app = FastAPI(title="Banking News Intelligence System")


@app.get("/")
def root():
    return {"status": "Backend running"}


@app.get("/news/youtube")
def youtube_news():
    return fetch_youtube_news(limit=10)
