from fastapi import APIRouter, Request, HTTPException, UploadFile, File
from app.models.schemas import SearchResponse, MovieResult

router = APIRouter()


@router.post("/transcribe", response_model=SearchResponse)
async def transcribe_and_search(
    request: Request,
    audio: UploadFile = File(...),
    top_k: int = 5,
):

    transcriber = request.app.state.transcriber
    embedder = request.app.state.embedder
    qdrant = request.app.state.qdrant

    # ── Step 1: Read audio bytes ─────────────────────────────
    audio_bytes = await audio.read()
    if not audio_bytes:
        raise HTTPException(status_code=400, detail="Audio file is empty")

    # ── Step 2: Transcribe ───────────────────────────────────
    try:
        transcript = transcriber.transcribe(
            audio_bytes,
            filename=audio.filename or "audio.webm"
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Transcription failed: {str(e)}")

    if not transcript:
        raise HTTPException(
            status_code=422,
            detail="Could not transcribe audio — please try again"
        )

    print(f"[Whisper] Transcribed: '{transcript}'")

    # ── Step 3: Embed + Search ────────────────────────────────
    try:
        vectors = embedder.embed(transcript)

        dense_results = qdrant.client.query_points(
            collection_name="movies",
            using="dense",
            query=vectors["dense"],
            limit=top_k,
            with_payload=True,
        )


        results = [
            MovieResult(
                tmdb_id=r.payload["tmdb_id"],
                score=r.score
            )
            for r in dense_results.points
        ]

        return SearchResponse(query=transcript, results=results)

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Search failed: {str(e)}"
        )