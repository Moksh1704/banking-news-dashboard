from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from backend.app.routes.news import router as news_router

app = FastAPI(title="Banking News Dashboard API")


# -----------------------------
# Health check (important for deployment)
# -----------------------------
@app.get("/health")
def health():
    return {"status": "ok"}


# -----------------------------
# Include routes
# -----------------------------
app.include_router(news_router, prefix="/news")


# -----------------------------
# Root
# -----------------------------
@app.get("/")
def root():
    return {"status": "API running"}


# -----------------------------
# Global exception handler
# Ensures backend ALWAYS returns JSON
# -----------------------------
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error"}
    )
