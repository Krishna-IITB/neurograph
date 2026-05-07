"""Recursive character splitter with configurable size + overlap.

Default 500-char chunks with 50-char overlap preserves semantic boundaries
across chunk edges (interview talking point: "I used overlapping chunking
to preserve semantic meaning across chunk boundaries").
"""

from langchain_core.documents import Document


def chunk_documents(
    docs: list[Document],
    chunk_size: int | None = None,
    chunk_overlap: int | None = None,
) -> list[Document]:
    """Split documents into overlapping chunks. Falls back to settings defaults."""
    raise NotImplementedError("Phase 1: implement chunker")
