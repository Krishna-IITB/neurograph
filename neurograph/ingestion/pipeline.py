"""Phase 1 orchestrator: load → chunk → clean → index.

Phase 1A: `run_ingestion()`         PDFs in  → cleaned chunks out
Phase 1B: `run_indexing(chunks)`    chunks in → ChromaDB + Neo4j updated
"""

from __future__ import annotations

from pathlib import Path

from langchain_core.documents import Document
from loguru import logger

from neurograph.generation.llm_client import is_available as llm_available
from neurograph.indexing import graph_store, vector_store
from neurograph.indexing.entity_resolver import resolve_triplets
from neurograph.indexing.triplet_extractor import extract_from_documents
from neurograph.ingestion.chunker import chunk_documents
from neurograph.ingestion.cleaner import clean_documents
from neurograph.ingestion.loader import load_directory, load_pdf


def run_ingestion(
    source: Path | str,
    *,
    use_llm_clean: bool = False,
    chunk_size: int | None = None,
    chunk_overlap: int | None = None,
) -> list[Document]:
    """Phase 1A: load PDFs → chunk → clean."""
    src = Path(source)
    logger.info(f"=== Phase 1A ingestion starting: {src} ===")

    if src.is_dir():
        raw = load_directory(src)
    elif src.is_file():
        raw = load_pdf(src)
    else:
        raise FileNotFoundError(f"No such path: {src}")

    if not raw:
        logger.warning("No content loaded — aborting")
        return []

    chunks = chunk_documents(raw, chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    cleaned = clean_documents(chunks, use_llm=use_llm_clean)
    logger.info(f"=== Phase 1A complete: {len(cleaned)} chunks ready ===")
    return cleaned


def run_indexing(
    chunks: list[Document],
    *,
    do_vector: bool = True,
    do_graph: bool = True,
    max_chunks_for_graph: int | None = None,
) -> dict:
    """Phase 1B: write chunks to vector + graph indexes.

    Args:
        chunks: Cleaned chunks from Phase 1A.
        do_vector: Push to ChromaDB. Has no external dependencies.
        do_graph: Extract triplets via LLM, then write to Neo4j. Requires
            both GROQ_API_KEY (or Ollama) and Neo4j credentials. Skipped
            with a warning if either is missing.
        max_chunks_for_graph: Optional cap on chunks fed to the triplet
            extractor (LLM is the bottleneck — ~500ms/chunk on Groq free).

    Returns:
        Summary dict: {"vectors": N, "triplets": M, "graph_nodes": K, "graph_rels": L}
    """
    summary = {"vectors": 0, "triplets": 0, "graph_nodes": 0, "graph_rels": 0}
    if not chunks:
        logger.warning("run_indexing called with empty chunks list")
        return summary

    logger.info(f"=== Phase 1B indexing starting: {len(chunks)} chunks ===")

    # ---- Vector path ----
    if do_vector:
        logger.info("→ Vector indexing (ChromaDB)")
        vector_store.upsert_documents(chunks)
        summary["vectors"] = vector_store.collection_size()
    else:
        logger.info("→ Vector indexing skipped (do_vector=False)")

    # ---- Graph path (with graceful degradation) ----
    if do_graph:
        if not llm_available():
            logger.warning(
                "→ Graph indexing skipped: no LLM provider configured "
                "(set GROQ_API_KEY or use Ollama)"
            )
        elif not graph_store.is_configured():
            logger.warning(
                "→ Graph indexing skipped: Neo4j credentials missing "
                "(set NEO4J_URI and NEO4J_PASSWORD in .env)"
            )
        else:
            logger.info("→ Graph indexing (triplet extract → resolve → Neo4j)")
            triplets = extract_from_documents(chunks, max_chunks=max_chunks_for_graph)
            summary["triplets"] = len(triplets)
            if triplets:
                resolved = resolve_triplets(triplets)
                graph_store.upsert_triplets(resolved)
                stats = graph_store.stats()
                summary["graph_nodes"] = stats.get("nodes", 0)
                summary["graph_rels"] = stats.get("rels", 0)
    else:
        logger.info("→ Graph indexing skipped (do_graph=False)")

    logger.info(f"=== Phase 1B complete: {summary} ===")
    return summary
