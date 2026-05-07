"""Unit tests for the chunker — no PDF fixtures needed."""

from langchain_core.documents import Document

from neurograph.ingestion.chunker import chunk_documents


def test_chunker_splits_long_text():
    docs = [
        Document(
            page_content="A" * 1500,
            metadata={"source": "test.pdf", "page": 1},
        )
    ]
    chunks = chunk_documents(docs, chunk_size=100, chunk_overlap=10)
    assert len(chunks) > 5, "Expected long text to produce many chunks"
    assert all(len(c.page_content) <= 100 for c in chunks)


def test_chunker_assigns_chunk_ids():
    docs = [Document(page_content="x " * 500, metadata={"source": "doc.pdf", "page": 3})]
    chunks = chunk_documents(docs, chunk_size=100, chunk_overlap=10)
    ids = [c.metadata["chunk_id"] for c in chunks]
    assert all(cid.startswith("doc:p3:c") for cid in ids)
    # IDs should be unique within a page
    assert len(set(ids)) == len(ids)


def test_chunker_preserves_metadata():
    docs = [
        Document(
            page_content="hello world " * 50,
            metadata={"source": "x.pdf", "page": 1, "extra": "keep_me"},
        )
    ]
    chunks = chunk_documents(docs, chunk_size=80, chunk_overlap=10)
    for c in chunks:
        assert c.metadata.get("source") == "x.pdf"
        assert c.metadata.get("page") == 1
        assert c.metadata.get("extra") == "keep_me"


def test_chunker_empty_input():
    assert chunk_documents([]) == []


def test_chunker_indices_restart_per_page():
    docs = [
        Document(page_content="A" * 300, metadata={"source": "f.pdf", "page": 1}),
        Document(page_content="B" * 300, metadata={"source": "f.pdf", "page": 2}),
    ]
    chunks = chunk_documents(docs, chunk_size=100, chunk_overlap=10)
    p1 = [c for c in chunks if c.metadata["page"] == 1]
    p2 = [c for c in chunks if c.metadata["page"] == 2]
    assert any(c.metadata["chunk_id"].endswith(":c0") for c in p1)
    assert any(c.metadata["chunk_id"].endswith(":c0") for c in p2)
