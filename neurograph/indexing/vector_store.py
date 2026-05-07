"""ChromaDB wrapper for the dense vector index.

Embedding model: sentence-transformers/all-MiniLM-L6-v2 (384-dim).
Persisted to disk under settings.chroma_persist_dir so the index survives
container restarts.
"""

from langchain_core.documents import Document


def upsert_documents(docs: list[Document]) -> None:
    """Embed and write chunks to ChromaDB."""
    raise NotImplementedError("Phase 1: implement Chroma upsert")


def search(query: str, k: int | None = None) -> list[Document]:
    """Top-k semantic search."""
    raise NotImplementedError("Phase 2: implement vector search")
