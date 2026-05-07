"""Recursive character splitter with configurable size + overlap.

Default 500-char chunks with 50-char overlap (from settings) preserves
semantic boundaries across chunk edges. The splitter respects paragraph
and sentence boundaries before falling back to characters.

Each output chunk gets a stable `chunk_id` in metadata of the form
"<filename>:p<page>:c<chunk_index>" — used for eval matching and
graph triplet provenance.
"""

from __future__ import annotations

from pathlib import Path

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from loguru import logger

from neurograph.config import settings


def chunk_documents(
    docs: list[Document],
    chunk_size: int | None = None,
    chunk_overlap: int | None = None,
) -> list[Document]:
    """Split each Document into overlapping chunks.

    Args:
        docs: Documents to split (typically one per PDF page).
        chunk_size: Override settings.chunk_size if given.
        chunk_overlap: Override settings.chunk_overlap if given.

    Returns:
        New list of Documents. Each has its parent's metadata plus a `chunk_id`.
    """
    size = chunk_size or settings.chunk_size
    overlap = chunk_overlap or settings.chunk_overlap

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=size,
        chunk_overlap=overlap,
        # Try to split on these in order — paragraph, line, sentence, then chars
        separators=["\n\n", "\n", ". ", " ", ""],
        length_function=len,
    )

    chunks: list[Document] = []
    # Counter per (source, page) so chunk indices restart per page
    page_counter: dict[tuple[str, int], int] = {}

    for doc in docs:
        source = doc.metadata.get("source", "unknown")
        page = doc.metadata.get("page", 0)
        sub = splitter.split_text(doc.page_content)
        for piece in sub:
            key = (source, page)
            idx = page_counter.get(key, 0)
            page_counter[key] = idx + 1
            chunk_id = f"{Path(source).stem}:p{page}:c{idx}"
            chunks.append(
                Document(
                    page_content=piece,
                    metadata={**doc.metadata, "chunk_id": chunk_id},
                )
            )

    logger.info(
        f"Chunked {len(docs)} documents into {len(chunks)} chunks "
        f"(size={size}, overlap={overlap})"
    )
    return chunks
