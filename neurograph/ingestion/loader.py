"""PDF loading.

Uses pdfplumber by default (better for column layouts and tables) with
pypdf as a lightweight fallback. Returns one langchain Document per page
so we keep page-level metadata for citation later.
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from langchain_core.documents import Document
from loguru import logger

Backend = Literal["pdfplumber", "pypdf"]


def load_pdf(path: Path | str, backend: Backend = "pdfplumber") -> list[Document]:
    """Load a single PDF as one Document per page.

    Args:
        path: Path to the .pdf file.
        backend: "pdfplumber" (default, more accurate) or "pypdf" (faster, simpler).

    Returns:
        List of Documents with metadata {source, page}.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"PDF not found: {path}")
    if path.suffix.lower() != ".pdf":
        raise ValueError(f"Not a PDF: {path}")

    if backend == "pdfplumber":
        import pdfplumber

        docs: list[Document] = []
        with pdfplumber.open(path) as pdf:
            for i, page in enumerate(pdf.pages, start=1):
                text = page.extract_text() or ""
                if not text.strip():
                    continue
                docs.append(
                    Document(
                        page_content=text,
                        metadata={"source": str(path), "page": i},
                    )
                )
        logger.info(f"Loaded {len(docs)} pages from {path.name} (pdfplumber)")
        return docs

    elif backend == "pypdf":
        from pypdf import PdfReader

        reader = PdfReader(str(path))
        docs = [
            Document(
                page_content=page.extract_text() or "",
                metadata={"source": str(path), "page": i + 1},
            )
            for i, page in enumerate(reader.pages)
            if (page.extract_text() or "").strip()
        ]
        logger.info(f"Loaded {len(docs)} pages from {path.name} (pypdf)")
        return docs

    else:
        raise ValueError(f"Unknown backend: {backend!r}")


def load_directory(path: Path | str, backend: Backend = "pdfplumber") -> list[Document]:
    """Load every .pdf in `path` (non-recursive)."""
    path = Path(path)
    if not path.is_dir():
        raise NotADirectoryError(f"Not a directory: {path}")

    pdfs = sorted(path.glob("*.pdf"))
    if not pdfs:
        logger.warning(f"No PDFs found in {path}")
        return []

    all_docs: list[Document] = []
    for pdf in pdfs:
        all_docs.extend(load_pdf(pdf, backend=backend))
    logger.info(f"Loaded {len(all_docs)} pages from {len(pdfs)} PDFs in {path}")
    return all_docs
