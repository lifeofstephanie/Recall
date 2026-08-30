from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from dotenv import load_dotenv

from app.routes import search
from app.services.embedding import EmbeddingService
from app.services.lancedb_service import LanceDBService

load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Runs on startup: load MiniLM model and connect to LanceDB Cloud.
    Both are kept warm in memory for the lifetime of the server.
    """
    print("🚀 Starting Gist AI Microservice...")

    print("   Loading MiniLM embedding model...")
    app.state.embedder = EmbeddingService()
    print("   ✅ Embedding model ready")

    print("   Connecting to LanceDB Cloud...")
    app.state.lancedb = LanceDBService()
    print("   ✅ LanceDB connected")

    print("🎬 Gist AI ready!\n")
    yield

    print("Shutting down Gist AI...")


app = FastAPI(
    title="Gist AI Microservice",
    description="Semantic search for movie identification using MiniLM embeddings and LanceDB",
    version="2.0.0",
    lifespan=lifespan,
)

app.include_router(search.router)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Catch-all error handler. Logs full traceback server-side but
    returns a generic message to the client to avoid leaking internals."""
    import traceback

    print("❌ CRITICAL PYTHON ERROR OCCURRED:")
    traceback.print_exc()
    return JSONResponse(
        status_code=500,
        content={"message": "Internal Server Error"},
    )


@app.get("/health")
def health():
    return {"status": "ok", "service": "gist-ai"}