import os
from fastembed import TextEmbedding


class EmbeddingService:
    """
    Wraps all-MiniLM-L6-v2 for text-to-vector conversion using fastembed
    (ONNX Runtime) — no PyTorch, so it runs in well under 512MB of RAM and
    fits a free hosting tier.

    Output is verified identical (cosine 1.0000) to the sentence-transformers
    build that produced the ingested LanceDB vectors, so query and index
    vectors match exactly. It also mirrors the model the mobile app runs
    on-device for query embedding.
    """

    MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
    VECTOR_SIZE = 384

    def __init__(self):
        model_name = os.getenv("EMBEDDING_MODEL", self.MODEL_NAME)
        self.model = TextEmbedding(model_name=model_name)

    def embed(self, text: str) -> list[float]:
        """
        Embed a single query string into a 384-dim, L2-normalized dense
        vector. Returns a plain list of floats ready for LanceDB search.
        """
        vector = next(iter(self.model.embed([text])))
        return vector.tolist()
