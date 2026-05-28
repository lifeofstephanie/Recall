from contextlib import asynccontextmanager
from fastapi import FastAPI
from dotenv import load_dotenv

from app.routes import search
from app.routes import transcribe
from app.services.embedding import EmbeddingService
from app.services.qdrant import QdrantService
from app.services.transcription import TranscriptionService

from fastapi import Request
from fastapi.responses import JSONResponse
import traceback

load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Runs on startup: load all models and connect to Qdrant.
    All models are loaded once and kept warm in memory.
    """
    print("🚀 Starting Gist AI Microservice...")

    print("   Loading BGE-M3 embedding model (first run may download ~2GB)...")
    app.state.embedder = EmbeddingService()
    print("   ✅ Embedding model ready")

    print("   Loading Whisper speech-to-text model...")
    app.state.transcriber = TranscriptionService()
    print("   ✅ Whisper model ready")

    print("   Connecting to Qdrant Cloud...")
    app.state.qdrant = QdrantService()
    print("   ✅ Qdrant connected")

    print("🎬 Gist AI ready!\n")
    yield

    print("Shutting down Gist AI...")


app = FastAPI(
    title="Gist AI Microservice",
    description="Hybrid semantic search + Whisper speech-to-text for movie identification",
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(search.router)
app.include_router(transcribe.router)

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    print("❌ CRITICAL PYTHON ERROR OCCURRED:")
    traceback.print_exc() # This will force the traceback into your terminal
    return JSONResponse(
        status_code=500,
        content={"message": f"Internal Server Error: {str(exc)}"}
    )

@app.get("/health")
def health():
    return {"status": "ok", "service": "gist-ai"}