from fastapi import APIRouter, Query
from backend.app.services.web_news import fetch_web_news
from backend.app.services.youtube_news import fetch_youtube_news
from backend.app.services.aggregator import aggregate_news

router = APIRouter()

@router.get("/web")
def get_web_news(
    keyword: str = Query("banking india"),
    limit: int = Query(10)
):
    return fetch_web_news(keyword, limit)

@router.get("/youtube")
def get_youtube_news(
    keyword: str = Query("banking news india"),
    limit: int = Query(10)
):
    return fetch_youtube_news(keyword, limit)


@router.get("/all")
def get_all_news(
    keyword: str = Query("banking india"),
    limit: int = Query(10)
):
    return aggregate_news(keyword, limit)
