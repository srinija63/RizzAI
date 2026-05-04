"""Embedding provider selection for RAG (OpenAI or local fallback)."""

from __future__ import annotations

from sentence_transformers import SentenceTransformer

from langchain_openai import OpenAIEmbeddings
from services.config import settings


class LocalSentenceTransformerEmbeddings:
    """LangChain-compatible wrapper around sentence-transformers."""

    def __init__(self, model_name: str):
        self.model = SentenceTransformer(model_name)

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


class ResilientEmbeddings:
    """
    Try OpenAI embeddings first, then fallback to local model on error.

    This prevents ingestion/retrieval failures when an API key exists but is invalid.
    """

    def __init__(
        self,
        openai_embeddings: OpenAIEmbeddings | None,
        local_embeddings: LocalSentenceTransformerEmbeddings,
    ):
        self._openai_embeddings = openai_embeddings
        self._local_embeddings = local_embeddings
        self._use_local_only = openai_embeddings is None

        if self._use_local_only:
            print("Falling back to local embeddings due to error: OPENAI_API_KEY missing")
        else:
            print("Using OpenAI embeddings")

    def _fallback(self, exc: Exception) -> None:
        if not self._use_local_only:
            self._use_local_only = True
            print(f"Falling back to local embeddings due to error: {exc!s}")

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if not self._use_local_only and self._openai_embeddings is not None:
            try:
                return self._openai_embeddings.embed_documents(texts)
            except Exception as exc:  # noqa: BLE001 - fallback on any provider issue
                self._fallback(exc)
        return self._local_embeddings.embed_documents(texts)

    def embed_query(self, text: str) -> list[float]:
        if not self._use_local_only and self._openai_embeddings is not None:
            try:
                return self._openai_embeddings.embed_query(text)
            except Exception as exc:  # noqa: BLE001 - fallback on any provider issue
                self._fallback(exc)
        return self._local_embeddings.embed_query(text)


def get_embeddings():
    """
    Return embedding model with automatic fallback behavior.

    - If OPENAI_API_KEY is set, use OpenAI-compatible embeddings.
    - If missing, fallback to local sentence-transformers model.
    """
    local_embeddings = LocalSentenceTransformerEmbeddings(settings.local_embedding_model)

    openai_embeddings = None
    if settings.openai_api_key:
        openai_embeddings = OpenAIEmbeddings(
            model=settings.openai_embedding_model,
            openai_api_key=settings.openai_api_key,
            base_url=settings.openai_base_url,
        )
    return ResilientEmbeddings(openai_embeddings, local_embeddings)

