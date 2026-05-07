"""CLI: `python -m scripts.ingest <pdf_or_dir> [flags]`

Runs the full ingestion + indexing pipeline.

Examples:
    # Phase 1A only — chunks but no indexing (fast, free, no creds needed)
    python -m scripts.ingest data/sample_pdfs

    # Vector indexing only (no LLM, no Neo4j needed)
    python -m scripts.ingest data/sample_pdfs --index --no-graph

    # Full Phase 1B (vector + graph)
    python -m scripts.ingest data/sample_pdfs --index

    # Quick graph smoke test on a small subset
    python -m scripts.ingest data/sample_pdfs --index --max-graph-chunks 30

    # Re-run with the LLM cleaning pass for higher-quality input
    python -m scripts.ingest data/sample_pdfs --index --llm-clean
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from loguru import logger

from neurograph.ingestion.pipeline import run_indexing, run_ingestion


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Ingest PDFs and (optionally) index to ChromaDB + Neo4j.",
    )
    parser.add_argument("source", type=Path, help="Path to a .pdf or directory of .pdfs.")

    parser.add_argument(
        "--llm-clean",
        action="store_true",
        help="Run the LLM cleaning pass before indexing (requires LLM provider).",
    )
    parser.add_argument(
        "--chunk-size", type=int, default=None,
        help="Override chunk size (default from .env).",
    )
    parser.add_argument(
        "--chunk-overlap", type=int, default=None,
        help="Override chunk overlap (default from .env).",
    )
    parser.add_argument(
        "--show", type=int, default=2,
        help="Print first N cleaned chunks for inspection.",
    )

    # ---- Indexing flags ----
    parser.add_argument(
        "--index", action="store_true",
        help="After ingestion, push chunks to vector + graph stores.",
    )
    parser.add_argument(
        "--no-vector", action="store_true",
        help="Skip vector indexing (only meaningful with --index).",
    )
    parser.add_argument(
        "--no-graph", action="store_true",
        help="Skip graph indexing (only meaningful with --index).",
    )
    parser.add_argument(
        "--max-graph-chunks", type=int, default=None,
        help="Cap chunks fed to the triplet extractor. Useful for smoke tests "
             "(LLM is the bottleneck).",
    )

    args = parser.parse_args()

    if not args.source.exists():
        logger.error(f"Path not found: {args.source}")
        sys.exit(1)

    chunks = run_ingestion(
        args.source,
        use_llm_clean=args.llm_clean,
        chunk_size=args.chunk_size,
        chunk_overlap=args.chunk_overlap,
    )

    if not chunks:
        logger.error("No chunks produced. Check the input PDFs.")
        sys.exit(1)

    sources = {c.metadata.get("source", "?") for c in chunks}
    pages = {(c.metadata.get("source"), c.metadata.get("page")) for c in chunks}
    avg_len = sum(len(c.page_content) for c in chunks) / len(chunks)

    print()
    print("=" * 70)
    print("  Phase 1A — Ingestion")
    print("=" * 70)
    print(f"  Files ingested : {len(sources)}")
    print(f"  Pages ingested : {len(pages)}")
    print(f"  Total chunks   : {len(chunks)}")
    print(f"  Avg chunk size : {avg_len:.0f} chars")
    print(f"  LLM clean      : {'on' if args.llm_clean else 'off (regex only)'}")
    print("=" * 70)

    print(f"\nFirst {min(args.show, len(chunks))} chunks:\n")
    for c in chunks[: args.show]:
        print(f"--- {c.metadata.get('chunk_id')} ---")
        print(c.page_content[:300] + ("..." if len(c.page_content) > 300 else ""))
        print()

    # ---- Optional Phase 1B ----
    if args.index:
        summary = run_indexing(
            chunks,
            do_vector=not args.no_vector,
            do_graph=not args.no_graph,
            max_chunks_for_graph=args.max_graph_chunks,
        )
        print()
        print("=" * 70)
        print("  Phase 1B — Indexing")
        print("=" * 70)
        print(f"  Vectors in ChromaDB     : {summary['vectors']}")
        print(f"  Triplets extracted      : {summary['triplets']}")
        print(f"  Nodes in Neo4j          : {summary['graph_nodes']}")
        print(f"  Relationships in Neo4j  : {summary['graph_rels']}")
        print("=" * 70)


if __name__ == "__main__":
    main()
