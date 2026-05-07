"""CLI: `python -m scripts.query "your question" [--mode hybrid|vector|graph]`

End-to-end Q&A. Prints the answer, retrieval mode, latency, and the
sources (vector chunks + graph paths) used to construct the answer.

Examples:
    python -m scripts.query "Who founded SpaceX?"
    python -m scripts.query "How is Elon Musk connected to Mars?" --mode hybrid
    python -m scripts.query "When was Tesla founded?" --mode vector --k 3
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from loguru import logger

from neurograph.generation.qa import answer


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Ask NeuroGraph a question (Phase 2 — retrieval + generation).",
    )
    parser.add_argument("question", help="Your question (in quotes).")
    parser.add_argument(
        "--mode", choices=["vector", "graph", "hybrid"], default="hybrid",
        help="Retrieval mode. Default: hybrid.",
    )
    parser.add_argument("--k", type=int, default=None, help="Vector top-k override.")
    parser.add_argument("--hops", type=int, default=None, help="Graph traversal hops override.")
    parser.add_argument(
        "--show-context", action="store_true",
        help="Print the formatted context that was sent to the LLM.",
    )
    parser.add_argument(
        "--quiet", action="store_true",
        help="Suppress debug logs from retrieval modules.",
    )

    args = parser.parse_args()

    if args.quiet:
        logger.remove()
        logger.add(sys.stderr, level="WARNING")

    if not args.question.strip():
        print("Question cannot be empty.")
        sys.exit(1)

    print()
    print("=" * 70)
    print(f"  Q: {args.question}")
    print(f"  Mode: {args.mode}")
    print("=" * 70)

    resp = answer(args.question, mode=args.mode, k=args.k, hops=args.hops)

    print()
    print("Answer:")
    print("-" * 70)
    print(resp.answer)
    print("-" * 70)
    print(f"  Latency: {resp.latency_ms:.0f} ms")
    print(f"  Vector chunks retrieved: {len(resp.retrieval.chunks)}")
    print(f"  Graph paths retrieved:   {len(resp.retrieval.paths)}")
    print()

    if resp.retrieval.chunks:
        print("Sources (vector):")
        for i, doc in enumerate(resp.retrieval.chunks, 1):
            src = Path(doc.metadata.get("source", "?")).name
            page = doc.metadata.get("page", "?")
            preview = doc.page_content.strip().replace("\n", " ")[:120]
            print(f"  [{i}] {src} p{page} — {preview}...")
        print()

    if resp.retrieval.paths:
        print("Sources (graph):")
        for p in resp.retrieval.paths[:10]:
            print(f"  • {p}")
        if len(resp.retrieval.paths) > 10:
            print(f"  ... and {len(resp.retrieval.paths) - 10} more paths")
        print()

    if args.show_context:
        from neurograph.retrieval.hybrid import format_context
        print("=" * 70)
        print("Context sent to LLM:")
        print("=" * 70)
        print(format_context(resp.retrieval.chunks, resp.retrieval.paths))
        print()


if __name__ == "__main__":
    main()
