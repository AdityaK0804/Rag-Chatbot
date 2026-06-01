import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
# Load environment variables first before importing local modules
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import ingest, chat


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Anything here runs once on startup before the first request.
    # Good place to validate the Gemini key exists so the server
    # fails loudly at boot rather than silently at the first chat request.
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY or GOOGLE_API_KEY is not set. Add it to your .env file.")
    print("[OK] Gemini API key found")
    print("[OK] Server ready")
    yield
    # Anything after yield runs on shutdown. Nothing to clean up yet.


app = FastAPI(
    title="Video RAG API",
    description="RAG chatbot that compares two social media videos.",
    version="1.0.0",
    lifespan=lifespan,
)

# Allow the Next.js dev server to call the API.
# In production you'd replace the wildcard with your actual domain.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(ingest.router, prefix="/api")
app.include_router(chat.router, prefix="/api")


@app.get("/health")
async def health():
    return {"status": "ok"}