from fastapi import APIRouter, Request, HTTPException
from app.models.schemas import SearchRequest, SearchResponse, MovieResult

router = APIRouter()


@router.post("/search", response_model=SearchResponse)
async def search(request: Request, body: SearchRequest):
    """
    POST /search
    Accepts a text query, vectorizes it with BGE-M3, and runs
    hybrid search against the Qdrant movie collection.
    """
    embedder = request.app.state.embedder
    qdrant = request.app.state.qdrant

    try:
        # Step 1: Vectorize the query (dense + sparse in one pass)
        vectors = embedder.embed(body.query)

        dense_results = qdrant.client.query_points(
            collection_name="movies",
            using="dense",
            query=vectors["dense"],
            limit=body.top_k,
            with_payload=True,
        )


        results = [
            MovieResult(tmdb_id=r.payload["tmdb_id"], score=r.score)
            for r in dense_results.points
        ]

        return SearchResponse(query=body.query, results=results)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")