from pydantic import BaseModel, Field


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=500, description="User's movie search query")
    top_k: int = Field(default=5, ge=1, le=20, description="Number of results to return")


class MovieResult(BaseModel):
    tmdb_id: int
    score: float


class SearchResponse(BaseModel):
    query: str
    results: list[MovieResult]