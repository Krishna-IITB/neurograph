"""Vector retrieval — top-k cosine similarity from ChromaDB.

Thin wrapper around `indexing.vector_store.search` so the retrieval
namespace owns the public API for Phase 2.
"""

from __future__ import annotations

from langchain_core.documents import Document
from loguru import logger

from neurograph.config import settings
from neurograph.indexing import vector_store


def retrieve(query: str, k: int | None = None) -> list[Document]:
    """Return top-k chunks ranked by cosine similarity.

    Args:
        query: Natural language question.
        k: Number of chunks to return. Defaults to settings.top_k_vector.

    Returns:
        List of Documents (page_content + metadata) sorted best-first.
    """
    k = k or settings.top_k_vector
    docs = vector_store.search(query, k=k)
    logger.debug(f"vector_retriever: '{query[:60]}' → {len(docs)} chunks")
    return docs
