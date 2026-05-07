"""FastAPI application — exposes ingestion + query endpoints."""

from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="NeuroGraph API", version="0.1.0")


class QueryRequest(BaseModel):
    question: str
    mode: str = "hybrid"  # "vector" | "graph" | "hybrid"


class QueryResponse(BaseModel):
    answer: str
    cached: bool
    mode: str
    latency_ms: float


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@app.post("/query", response_model=QueryResponse)
async def query(req: QueryRequest) -> QueryResponse:
    raise NotImplementedError("Phase 2: wire up query endpoint")
