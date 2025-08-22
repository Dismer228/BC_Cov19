from fastapi import FastAPI

from .routers import data, comments

app = FastAPI(
    title="BC_Cov19 API",
    version="0.1.0",
    description="API for querying Snowflake data with supplementary MongoDB metadata",
)

app.include_router(data.router, prefix="/data", tags=["data"])
app.include_router(comments.router, prefix="/comments", tags=["comments"])


@app.get("/health")
def healthcheck() -> dict:
    return {"status": "ok"}