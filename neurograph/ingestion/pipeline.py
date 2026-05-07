"""Phase 1 orchestrator: load → chunk → clean → return ready chunks."""

from pathlib import Path

from langchain_core.documents import Document


def run_ingestion(source: Path, *, clean: bool = True) -> list[Document]:
    """Full ingestion pipeline.

    Args:
        source: Path to a single PDF or a directory of PDFs.
        clean: If True, run the LLM cleaner over chunks before returning.

    Returns:
        Cleaned, chunked Documents ready for parallel indexing.
    """
    raise NotImplementedError("Phase 1: orchestrator")
