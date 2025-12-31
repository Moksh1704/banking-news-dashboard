from fastapi import FastAPI
from backend.app.routes import news

app = FastAPI(title="Banking News Dashboard API")

app.include_router(news.router, prefix="/news")

@app.get("/")
def root():
    return {"status": "API running"}
