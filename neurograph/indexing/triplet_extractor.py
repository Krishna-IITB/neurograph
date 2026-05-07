"""LLM-based triplet extraction.

For each cleaned chunk, asks the LLM to return a JSON array of
(head, relation, tail) triplets. We're defensive about parsing because
LLMs occasionally wrap JSON in markdown fences or add commentary.

Example input:  "Elon Musk is the CEO of Tesla."
Example output: [Triplet(head="Elon Musk", relation="CEO_OF", tail="Tesla")]
"""

from __future__ import annotations

import json
import re

from langchain_core.documents import Document
from loguru import logger
from pydantic import BaseModel, Field, ValidationError
from tqdm import tqdm

from neurograph.generation.llm_client import complete, is_available
from neurograph.generation.prompts import TRIPLET_PROMPT


class Triplet(BaseModel):
    head: str = Field(..., min_length=1, max_length=200)
    relation: str = Field(..., min_length=1, max_length=100)
    tail: str = Field(..., min_length=1, max_length=200)
    source_chunk_id: str | None = None


# ---------- defensive JSON extraction ----------

_FENCE_RE = re.compile(r"```(?:json)?\s*|\s*```$", re.MULTILINE)


def _extract_json_array(text: str) -> list[dict]:
    """Pull the first JSON array out of an LLM response. Returns [] on failure."""
    if not text:
        return []
    cleaned = _FENCE_RE.sub("", text.strip())
    start = cleaned.find("[")
    end = cleaned.rfind("]")
    if start == -1 or end == -1 or end <= start:
        return []
    try:
        parsed = json.loads(cleaned[start : end + 1])
        return parsed if isinstance(parsed, list) else []
    except json.JSONDecodeError:
        return []


def _normalize_relation(rel: str) -> str:
    """Force UPPERCASE_SNAKE_CASE for relation names, strip non-identifiers."""
    rel = rel.strip().upper()
    rel = re.sub(r"\s+", "_", rel)
    rel = re.sub(r"[^A-Z0-9_]", "", rel)
    rel = re.sub(r"_+", "_", rel).strip("_")
    return rel or "RELATED_TO"


# ---------- single-chunk extraction ----------


def extract_triplets(text: str, *, source_chunk_id: str | None = None) -> list[Triplet]:
    """Run a single LLM extraction pass. Returns 0..N triplets."""
    if not text or not text.strip():
        return []

    prompt = TRIPLET_PROMPT.format(text=text)
    try:
        raw = complete(prompt, temperature=0.0, max_tokens=1024)
    except Exception as e:
        logger.warning(f"LLM call failed for {source_chunk_id}: {e}")
        return []

    items = _extract_json_array(raw)
    triplets: list[Triplet] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        try:
            t = Triplet(
                head=str(item.get("head", "")).strip(),
                relation=_normalize_relation(str(item.get("relation", ""))),
                tail=str(item.get("tail", "")).strip(),
                source_chunk_id=source_chunk_id,
            )
            triplets.append(t)
        except ValidationError:
            continue
    return triplets


# ---------- batch ----------


def extract_from_documents(
    docs: list[Document],
    *,
    max_chunks: int | None = None,
) -> list[Triplet]:
    """Extract triplets from a batch of cleaned chunks.

    Args:
        docs: Cleaned chunks from Phase 1A.
        max_chunks: Optional cap (useful for fast smoke tests).

    Returns:
        Flat list of all triplets across all chunks.
    """
    if not is_available():
        logger.warning(
            "No LLM credentials configured — returning [] from triplet extractor. "
            "Set GROQ_API_KEY in .env (or run Ollama)."
        )
        return []

    if max_chunks:
        docs = docs[:max_chunks]
        logger.info(f"Limiting triplet extraction to first {max_chunks} chunks")

    all_triplets: list[Triplet] = []
    for doc in tqdm(docs, desc="Extracting triplets", unit="chunk"):
        cid = doc.metadata.get("chunk_id")
        all_triplets.extend(extract_triplets(doc.page_content, source_chunk_id=cid))

    logger.info(
        f"Extracted {len(all_triplets)} triplets from {len(docs)} chunks "
        f"(avg {len(all_triplets) / max(1, len(docs)):.1f} per chunk)"
    )
    return all_triplets
