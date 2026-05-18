"""Local sentence-transformer embeddings for RAG (singleton — load once, reuse)."""

from __future__ import annotations

import logging

from sentence_transformers import SentenceTransformer

from services.config import settings

logger = logging.getLogger("rizzai.embeddings")

_embeddings_instance: "LocalSentenceTransformerEmbeddings | None" = None


class LocalSentenceTransformerEmbeddings:
    """LangChain-compatible wrapper around sentence-transformers."""

    def __init__(self, model_name: str):
        logger.info("Loading embedding model: %s", model_name)
        self.model = SentenceTransformer(model_name)
        logger.info("Embedding model ready: %s", model_name)

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        vectors = self.model.encode(
            texts,
            normalize_embeddings=True,
            convert_to_numpy=True,
        )
        return vectors.tolist()

    def embed_query(self, text: str) -> list[float]:
        vector = self.model.encode(
            text,
            normalize_embeddings=True,
            convert_to_numpy=True,
        )
        return vector.tolist()


def get_embeddings() -> LocalSentenceTransformerEmbeddings:
    """Return the shared embedding model (loaded once per server process)."""
    global _embeddings_instance
    if _embeddings_instance is None:
        _embeddings_instance = LocalSentenceTransformerEmbeddings(
            settings.local_embedding_model
        )
    return _embeddings_instance


def preload_embeddings() -> None:
    """Warm up the embedding model at startup (optional, avoids first-request delay)."""
    get_embeddings()
