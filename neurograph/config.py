"""Central configuration loaded from environment variables.

All modules import `settings` from here — never read os.environ directly.
"""

from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Strongly typed settings backed by .env."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # ---- LLM provider ----
    llm_provider: Literal["groq", "ollama"] = "groq"

    # Groq
    groq_api_key: str = ""
    groq_model: str = "llama-3.1-70b-versatile"

    # Ollama
    ollama_host: str = "http://localhost:11434"
    ollama_model: str = "llama3.1:8b"

    # ---- Embeddings ----
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    embedding_dim: int = 384

    # ---- Vector DB ----
    chroma_persist_dir: Path = Path("./data/chroma")
    chroma_collection: str = "neurograph"

    # ---- Graph DB ----
    neo4j_uri: str = ""
    neo4j_user: str = "neo4j"
    neo4j_password: str = ""

    # ---- Cache ----
    redis_url: str = ""
    cache_threshold: float = Field(0.95, ge=0.0, le=1.0)

    # ---- Chunking ----
    chunk_size: int = 500
    chunk_overlap: int = 50

    # ---- Retrieval ----
    top_k_vector: int = 5
    graph_hops: int = 2

    # ---- API / UI ----
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    ui_port: int = 8501
    log_level: str = "INFO"


settings = Settings()
