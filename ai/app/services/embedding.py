import os
from sentence_transformers import SentenceTransformer


class EmbeddingService:
    """
    Wraps the all-MiniLM-L6-v2 model for text-to-vector conversion.

    MiniLM produces 384-dimensional dense vectors optimized for
    English semantic similarity. It matches the model used by:
    - The ingestion script (ingest.py) for subtitle embedding
    - The mobile app (on-device via ExecuTorch) for query embedding

    At ~80MB, it's lightweight enough to run on any free hosting tier.
    """

    MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
    VECTOR_SIZE = 384

    def __init__(self):
        model_name = os.getenv("EMBEDDING_MODEL", self.MODEL_NAME)
        self.model = SentenceTransformer(model_name)

    def embed(self, text: str) -> list[float]:
        """
        Embed a single query string into a 384-dim dense vector.
        Returns a plain list of floats ready for LanceDB search.
        """
        vector = self.model.encode([text])[0].tolist()
        return vector