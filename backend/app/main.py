from fastapi import FastAPI

app = FastAPI(title="Banking News Dashboard API")

@app.get("/")
def root():
    return {"status": "API running"}
