"""Unit tests for the regex cleaner — no LLM needed."""

from langchain_core.documents import Document

from neurograph.ingestion.cleaner import clean_documents, light_clean


def test_light_clean_fixes_hyphenation():
    text = "The compa-\nny was founded"
    assert light_clean(text) == "The company was founded"


def test_light_clean_strips_page_numbers():
    text = "Some content\n\n42\n\nMore content"
    out = light_clean(text)
    assert "42" not in out


def test_light_clean_collapses_whitespace():
    text = "hello    world   foo"
    assert light_clean(text) == "hello world foo"


def test_light_clean_collapses_newlines():
    text = "para 1\n\n\n\n\npara 2"
    assert "\n\n\n" not in light_clean(text)


def test_clean_documents_preserves_metadata():
    docs = [
        Document(
            page_content="The compa-\nny is great",
            metadata={"source": "x.pdf", "page": 1, "chunk_id": "x:p1:c0"},
        )
    ]
    out = clean_documents(docs, use_llm=False)
    assert len(out) == 1
    assert out[0].metadata["chunk_id"] == "x:p1:c0"
    assert "company" in out[0].page_content


def test_clean_documents_llm_falls_back_without_credentials(monkeypatch):
    """If use_llm=True but no creds, must not raise — falls back to light only."""
    monkeypatch.setenv("GROQ_API_KEY", "")
    docs = [Document(page_content="test", metadata={"chunk_id": "t:p1:c0"})]
    # Should not raise
    out = clean_documents(docs, use_llm=True)
    assert len(out) == 1
