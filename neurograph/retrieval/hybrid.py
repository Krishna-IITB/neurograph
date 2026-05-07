"""Hybrid retrieval — run vector + graph in parallel, format combined context.

The output of `retrieve()` is the string that gets dropped into the
generation prompt under the `{context}` slot. Format:

    Context from text:
    [1] (source: Tesla.pdf p4)
    Tesla, Inc. is an American multinational automotive...

    [2] (source: SpaceX.pdf p1)
    SpaceX, founded in 2002 by Elon Musk...

    Context from graph:
    - Elon Musk --FOUNDED--> SpaceX
    - Elon Musk --CEO_OF--> Tesla
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from langchain_core.documents import Document
from loguru import logger

from neurograph.retrieval import graph_retriever, vector_retriever

Mode = Literal["vector", "graph", "hybrid"]


@dataclass
class RetrievalResult:
    """Raw retrieval output. Useful for eval and the UI's source panel."""

    chunks: list[Document]
    paths: list[str]
    mode: Mode

    def has_content(self) -> bool:
        return bool(self.chunks) or bool(self.paths)


def _format_chunks(chunks: list[Document]) -> str:
    if not chunks:
        return ""
    lines = ["Context from text:"]
    for i, doc in enumerate(chunks, start=1):
        src = doc.metadata.get("source", "?")
        page = doc.metadata.get("page", "?")
        # Drop the directory from the source path for readability
        src_name = Path(src).name if src != "?" else "?"
        lines.append(f"[{i}] (source: {src_name} p{page})")
        lines.append(doc.page_content.strip())
        lines.append("")  # blank line between chunks
    return "\n".join(lines).rstrip()


def _format_paths(paths: list[str]) -> str:
    if not paths:
        return ""
    lines = ["Context from graph:"]
    lines.extend(f"- {p}" for p in paths)
    return "\n".join(lines)


def format_context(chunks: list[Document], paths: list[str]) -> str:
    """Build the combined context string for the generation prompt."""
    parts = [s for s in (_format_chunks(chunks), _format_paths(paths)) if s]
    return "\n\n".join(parts) if parts else "(no context retrieved)"


def retrieve(
    query: str,
    mode: Mode = "hybrid",
    *,
    k: int | None = None,
    hops: int | None = None,
) -> RetrievalResult:
    """Run retrieval in the requested mode.

    Args:
        query: User question.
        mode: "vector", "graph", or "hybrid". Hybrid runs both in parallel.
        k: Vector top-k override.
        hops: Graph traversal hops override.
    """
    chunks: list[Document] = []
    paths: list[str] = []

    if mode == "vector":
        chunks = vector_retriever.retrieve(query, k=k)
    elif mode == "graph":
        paths = graph_retriever.retrieve(query, hops=hops)
    elif mode == "hybrid":
        # Run both concurrently — they hit different services
        with ThreadPoolExecutor(max_workers=2) as ex:
            f_vec = ex.submit(vector_retriever.retrieve, query, k)
            f_gr = ex.submit(graph_retriever.retrieve, query, hops)
            chunks = f_vec.result()
            paths = f_gr.result()
    else:
        raise ValueError(f"Unknown mode: {mode!r}. Use 'vector', 'graph', or 'hybrid'.")

    logger.debug(
        f"Retrieval mode={mode}: {len(chunks)} chunks, {len(paths)} paths"
    )
    return RetrievalResult(chunks=chunks, paths=paths, mode=mode)
