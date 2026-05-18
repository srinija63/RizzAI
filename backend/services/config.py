"""Application settings loaded from environment variables."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Server and optional AI provider settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    host: str = "0.0.0.0"
    port: int = 8000

    gemini_api_key: str | None = None
    gemini_model: str = "gemini-2.0-flash"

    local_embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"

    ollama_base_url: str = "http://localhost:11434"
    ollama_models: str = "tinyllama,phi3,llama3"

    chroma_persist_dir: str = "./chroma_db"
    chroma_collection: str = "reply_patterns"

    # Reply coaching speed: skip Gemini analyze (tone is user-picked; intent uses rules).
    skip_llm_analyze: bool = True
    preload_embeddings: bool = True


settings = Settings()
