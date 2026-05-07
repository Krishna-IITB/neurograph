"""ChromaDB-backed dense vector index.

Embedding model: sentence-transformers/all-MiniLM-L6-v2 (384-dim).
Persisted to disk under settings.chroma_persist_dir so the index survives
container/process restarts.

The chunk's `chunk_id` (e.g. "tesla:p3:c2") is used as the ChromaDB
document ID — this gives us idempotent upserts (re-ingesting the same
PDF replaces rather than duplicates) and makes eval matching trivial
("did the retriever return the gold chunk_id?").
"""

from __future__ import annotations

import logging
from functools import lru_cache

import chromadb
from langchain_core.documents import Document
from loguru import logger
from sentence_transformers import SentenceTransformer

from neurograph.config import settings

# Quiet ChromaDB's chatty internal logger
logging.getLogger("chromadb").setLevel(logging.WARNING)


class _VectorStore:
    """Thin wrapper around a Chroma persistent collection + a local embedder."""

    def __init__(self) -> None:
        settings.chroma_persist_dir.mkdir(parents=True, exist_ok=True)
        self._client = chromadb.PersistentClient(path=str(settings.chroma_persist_dir))
        self._collection = self._client.get_or_create_collection(
            name=settings.chroma_collection,
            metadata={"hnsw:space": "cosine"},
        )
        logger.info(f"Loading embedding model: {settings.embedding_model}")
        # SentenceTransformer auto-detects MPS on Apple Silicon
        self._embedder = SentenceTransformer(settings.embedding_model)
        logger.info(
            f"Vector store ready (collection='{settings.chroma_collection}', "
            f"existing={self._collection.count()})"
        )

    def upsert(self, docs: list[Document], batch_size: int = 64) -> None:
        if not docs:
            logger.warning("upsert called with empty docs list")
            return
        ids = [d.metadata["chunk_id"] for d in docs]
        texts = [d.page_content for d in docs]
        # Chroma metadata must be primitive (str/int/float/bool) — coerce
        metadatas = [
            {k: (v if isinstance(v, (str, int, float, bool)) else str(v))
             for k, v in d.metadata.items()}
            for d in docs
        ]

        logger.info(f"Embedding {len(texts)} chunks with {settings.embedding_model}")
        embeddings = self._embedder.encode(
            texts, show_progress_bar=True, batch_size=batch_size
        ).tolist()

        # Chroma upsert handles batching internally but we chunk anyway for memory
        for i in range(0, len(ids), batch_size):
            self._collection.upsert(
                ids=ids[i : i + batch_size],
                embeddings=embeddings[i : i + batch_size],
                documents=texts[i : i + batch_size],
                metadatas=metadatas[i : i + batch_size],
            )
        logger.info(f"Upserted {len(ids)} chunks (collection size: {self._collection.count()})")

    def search(self, query: str, k: int | None = None) -> list[Document]:
        k = k or settings.top_k_vector
        emb = self._embedder.encode([query]).tolist()
        result = self._collection.query(query_embeddings=emb, n_results=k)
        docs = result.get("documents", [[]])[0]
        metas = result.get("metadatas", [[]])[0]
        return [Document(page_content=d, metadata=m) for d, m in zip(docs, metas)]

    def count(self) -> int:
        return self._collection.count()

    def reset(self) -> None:
        """Drop and recreate the collection. For dev/testing only."""
        self._client.delete_collection(settings.chroma_collection)
        self._collection = self._client.get_or_create_collection(
            name=settings.chroma_collection,
            metadata={"hnsw:space": "cosine"},
        )


@lru_cache(maxsize=1)
def _store() -> _VectorStore:
    return _VectorStore()


# Public functional API ------------------------------------------------------


def upsert_documents(docs: list[Document]) -> None:
    """Embed and write chunks to ChromaDB."""
    _store().upsert(docs)


def search(query: str, k: int | None = None) -> list[Document]:
    """Top-k semantic search."""
    return _store().search(query, k)


def collection_size() -> int:
    return _store().count()


def reset() -> None:
    _store().reset()
