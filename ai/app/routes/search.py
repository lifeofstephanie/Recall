from fastapi import APIRouter, Request, HTTPException
from app.models.schemas import SearchRequest, SearchResponse, MovieResult

router = APIRouter()


@router.post("/search", response_model=SearchResponse)
async def search(request: Request, body: SearchRequest):
    """
    POST /search
    Accepts a text query, vectorizes it with MiniLM, and runs
    vector search against the LanceDB movie quotes collection.

    Results are deduplicated by tmdb_id so each movie appears once.
    """
    embedder = request.app.state.embedder
    lancedb = request.app.state.lancedb

    try:
        # Step 1: Embed the query text into a 384-dim vector
        query_vector = embedder.embed(body.query)

        # Step 2: Search LanceDB (handles dedup internally)
        raw_results = lancedb.search(query_vector, top_k=body.top_k)

        # Step 3: Format response
        results = [
            MovieResult(tmdb_id=r["tmdb_id"], score=r["score"])
            for r in raw_results
        ]

        return SearchResponse(query=body.query, results=results)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")