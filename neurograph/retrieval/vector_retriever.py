"""Vector retrieval — top-k cosine similarity from ChromaDB."""

from langchain_core.documents import Document


def retrieve(query: str, k: int | None = None) -> list[Document]:
    raise NotImplementedError("Phase 2: vector retrieval")
