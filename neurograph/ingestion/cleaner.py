"""LLM-based semantic cleaner.

PDFs are messy: OCR artifacts, broken words, headers/footers, hyphenation.
We pass each chunk through a lightweight LLM call to produce a clean,
canonical version before downstream embedding + triplet extraction.

Talking point: "I added an LLM cleaning layer to improve data quality
before indexing — garbage in, garbage out."
"""

from langchain_core.documents import Document


def clean_chunk(text: str) -> str:
    """Send a single chunk through the LLM cleaner. Returns cleaned text."""
    raise NotImplementedError("Phase 1: implement LLM cleaner")


def clean_documents(docs: list[Document]) -> list[Document]:
    """Map clean_chunk over a batch with progress reporting."""
    raise NotImplementedError("Phase 1: implement batch cleaner")
