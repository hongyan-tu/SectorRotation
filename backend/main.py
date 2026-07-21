from fastapi import FastAPI
from pydantic import BaseModel
from typing import List, Dict, Any

app = FastAPI()

class TickerData(BaseModel):
    ticker: str
    data: List[Dict[str, Any]]

@app.get("/api/v1/health")
async def health():
    return {"status": "ok"}

@app.post("/api/v1/score")
async def score(tickers: List[str]):
    # placeholder: return mock rankings
    return {"timestamp": "2026-07-21T00:00:00Z", "rankings": [{"ticker":"XLK","score":1.0,"confidence":0.9}]}