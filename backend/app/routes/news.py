from fastapi import APIRouter, Query
from backend.app.services.google_news_rss import fetch_google_news
from backend.app.services.youtube_news import fetch_youtube_news

router = APIRouter()


@router.get("/google")
def get_google_news(
    keyword: str = Query("banking india"),
    limit: int = Query(10)
):
    _ = keyword
    return fetch_google_news(limit=limit)


@router.get("/youtube")
def get_youtube_news(
    keyword: str = Query("banking news india"),
    limit: int = Query(10)
):
    _ = keyword
    return fetch_youtube_news(limit=limit)


@router.get("/all")
def get_all_news(
    keyword: str = Query("banking india"),
    limit: int = Query(10)
):
    _ = keyword
    google_news = fetch_google_news(limit=limit)
    youtube_news = fetch_youtube_news(limit=limit)
    return google_news + youtube_news
