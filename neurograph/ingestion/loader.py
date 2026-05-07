"""PDF loading via PyPDFLoader (LangChain).

Reads a PDF (or directory of PDFs) and returns LangChain `Document` objects
with page-level metadata preserved.
"""

from pathlib import Path
from typing import Iterable

from langchain_core.documents import Document


def load_pdf(path: Path) -> list[Document]:
    """Load a single PDF into per-page Document objects."""
    raise NotImplementedError("Phase 1: implement PDF loader")


def load_directory(path: Path) -> list[Document]:
    """Load every .pdf in the given directory."""
    raise NotImplementedError("Phase 1: implement directory loader")
