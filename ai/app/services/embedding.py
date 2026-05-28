import os
from FlagEmbedding import BGEM3FlagModel


class EmbeddingService:
    """
    Wraps the BAAI/bge-m3 model.

    BGE-M3 produces TWO types of vectors from a single pass:
    - Dense vectors  → capture semantic meaning / plot vibes
    - Sparse vectors → capture exact keyword / quote matches

    Both are used together in Qdrant's Hybrid Search (Reciprocal Rank Fusion).
    """

    def __init__(self):
        model_name = os.getenv("EMBEDDING_MODEL", "BAAI/bge-m3")

        # use_fp16=True halves memory usage with negligible quality loss
        # Great for free-tier hosting on Hugging Face Spaces
        self.model = BGEM3FlagModel(model_name, use_fp16=True)

    def embed(self, text: str) -> dict:
        """
        Embed a single query string.
        Returns both dense and sparse vectors ready for Qdrant.
        """
        output = self.model.encode(
            [text],
            return_dense=True,
            return_sparse=True,
            return_colbert_vecs=False,  # Not needed for this use case
        )

        dense_vector = output["dense_vecs"][0].tolist()

        # Sparse vector: convert from {token_id: weight} to Qdrant format
        sparse_weights = output["lexical_weights"][0]
        sparse_indices = [int(k) for k in sparse_weights.keys()]
        sparse_values = [float(v) for v in sparse_weights.values()]

        return {
            "dense": dense_vector,
            "sparse": {
                "indices": sparse_indices,
                "values": sparse_values,
            },
        }