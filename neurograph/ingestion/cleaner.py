"""Two-pass cleaner for chunked PDF text.

Pass 1 — `light_clean` (always runs, free):
    Regex fixes for common PDF artifacts: hyphenated line breaks,
    runs of whitespace, repeated newlines, page-number-only lines.

Pass 2 — `llm_clean` (opt-in, costs LLM calls):
    Sends each chunk through Llama-3.1 with a strict prompt that says
    "fix OCR/formatting errors but do not add information." Skipped
    automatically if no LLM credentials are configured.

Talking point: "I added an LLM-based cleaning layer to improve data
quality before indexing — garbage in, garbage out."
"""

from __future__ import annotations

import re

from langchain_core.documents import Document
from loguru import logger
from tqdm import tqdm

from neurograph.generation.llm_client import complete, is_available
from neurograph.generation.prompts import CLEANER_PROMPT

# ---------- Pass 1: regex ----------

# Hyphenated word broken across a line: "compa-\nny" -> "company"
_HYPHEN_RE = re.compile(r"(\w)-\n(\w)")
# Standalone numeric lines (page numbers): " 12 \n"
_PAGE_NUM_RE = re.compile(r"^\s*\d{1,4}\s*$", re.MULTILINE)
# 3+ newlines collapse to 2
_NEWLINES_RE = re.compile(r"\n{3,}")
# Multiple spaces / tabs -> single space (NOT newlines)
_SPACES_RE = re.compile(r"[ \t]{2,}")


def light_clean(text: str) -> str:
    """Fast regex pass — fixes the obvious PDF extraction artifacts."""
    text = _HYPHEN_RE.sub(r"\1\2", text)
    text = _PAGE_NUM_RE.sub("", text)
    text = _NEWLINES_RE.sub("\n\n", text)
    text = _SPACES_RE.sub(" ", text)
    return text.strip()


# ---------- Pass 2: LLM ----------


def llm_clean(text: str) -> str:
    """Send a single chunk through the LLM cleaner. Returns cleaned text."""
    prompt = CLEANER_PROMPT.format(text=text)
    try:
        cleaned = complete(prompt, temperature=0.0, max_tokens=len(text) + 200)
        return cleaned.strip() or text
    except Exception as e:
        logger.warning(f"LLM clean failed, returning original: {e}")
        return text


# ---------- Batch orchestrator ----------


def clean_documents(
    docs: list[Document],
    *,
    use_llm: bool = False,
) -> list[Document]:
    """Apply light_clean to all docs; optionally also llm_clean.

    Args:
        docs: Chunked documents.
        use_llm: If True, also run the LLM cleaner. Requires GROQ_API_KEY
            (or a running Ollama). Falls back to light-only with a warning
            if the provider isn't configured.

    Returns:
        New list of Documents with cleaned page_content. Metadata preserved.
    """
    if use_llm and not is_available():
        logger.warning(
            "use_llm=True but no LLM credentials configured — "
            "falling back to light_clean only. Set GROQ_API_KEY in .env."
        )
        use_llm = False

    cleaned: list[Document] = []
    iterator = tqdm(docs, desc="Cleaning", unit="chunk") if use_llm else docs

    for doc in iterator:
        text = light_clean(doc.page_content)
        if use_llm and text:
            text = llm_clean(text)
        cleaned.append(Document(page_content=text, metadata=doc.metadata))

    logger.info(
        f"Cleaned {len(cleaned)} chunks "
        f"(light{'+LLM' if use_llm else ''})"
    )
    return cleaned
