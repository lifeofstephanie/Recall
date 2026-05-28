import os
from qdrant_client import QdrantClient
from qdrant_client.models import (
    VectorParams,
    SparseVectorParams,
    Distance,
    SparseIndexParams,
    NamedVector,
    NamedSparseVector,
    SparseVector,
    Prefetch,
    FusionQuery,
    Fusion,
)


COLLECTION_NAME = os.getenv("QDRANT_COLLECTION_NAME", "movies")
DENSE_VECTOR_SIZE = 1024  # BGE-M3 output dimension


class QdrantService:
    """
    Handles all Qdrant Cloud interactions:
    - Collection creation (run once during ingestion)
    - Hybrid search using Reciprocal Rank Fusion (dense + sparse)
    """

    def __init__(self):
        self.client = QdrantClient(
            url=os.getenv("QDRANT_URL"),
            api_key=os.getenv("QDRANT_API_KEY"),
        )
        self.collection = COLLECTION_NAME

    def hybrid_search(self, dense_vector: list, sparse_vector: dict, top_k: int = 5) -> list:
        results = self.client.query_points(
            collection_name=self.collection,
            prefetch=[
                Prefetch(
                    query=dense_vector,
                    using="dense",
                    limit=top_k * 3,
                ),
                Prefetch(
                    query=SparseVector(
                        indices=sparse_vector["indices"],
                        values=sparse_vector["values"],
                    ),
                    using="sparse",
                    limit=top_k * 3,
                ),
            ],
            query=Fusion.RRF,  # ✅ THIS is the correct way
            limit=top_k,
            with_payload=True,
        )

        return [
            {
                "tmdb_id": point.payload["tmdb_id"],
                "score": point.score,
            }
            for point in results.points
        ]

    def ensure_collection_exists(self):
        """
        Creates the movies collection in Qdrant if it doesn't already exist.
        Call this once before running the ingestion script.
        """
        existing = [c.name for c in self.client.get_collections().collections]
        if self.collection in existing:
            print(f"Collection '{self.collection}' already exists — skipping creation.")
            return

        self.client.create_collection(
            collection_name=self.collection,
            vectors_config={
                "dense": VectorParams(
                    size=DENSE_VECTOR_SIZE,
                    distance=Distance.COSINE,
                ),
            },
            sparse_vectors_config={
                "sparse": SparseVectorParams(
                    index=SparseIndexParams(on_disk=False)
                ),
            },
        )
        print(f"✅ Collection '{self.collection}' created.")