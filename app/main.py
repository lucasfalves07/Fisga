from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from app.scoring import score_email, score_url

WEB = Path(__file__).resolve().parent.parent / "web"

app = FastAPI(title="Fisga", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["POST", "GET"],
    allow_headers=["*"],
)


class UrlIn(BaseModel):
    url: str = Field(min_length=3, max_length=2048)


class EmailIn(BaseModel):
    raw: str = Field(min_length=1, max_length=200_000)


@app.get("/", include_in_schema=False)
def index():
    return FileResponse(WEB / "index.html")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/analyze/url")
def analyze_url(body: UrlIn):
    return score_url(body.url)


@app.post("/analyze/email")
def analyze_email(body: EmailIn):
    return score_email(body.raw)
