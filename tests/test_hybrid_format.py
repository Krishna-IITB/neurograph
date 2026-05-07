"""Unit tests for hybrid retrieval formatters."""

from langchain_core.documents import Document

from neurograph.retrieval.hybrid import _format_chunks, _format_paths, format_context


def test_format_chunks_empty():
    assert _format_chunks([]) == ""


def test_format_chunks_single():
    docs = [
        Document(
            page_content="Tesla is an EV company.",
            metadata={"source": "data/sample_pdfs/Tesla.pdf", "page": 4},
        )
    ]
    out = _format_chunks(docs)
    assert "Context from text:" in out
    assert "Tesla.pdf" in out  # directory stripped
    assert "data/sample_pdfs" not in out
    assert "p4" in out
    assert "Tesla is an EV company." in out


def test_format_paths_empty():
    assert _format_paths([]) == ""


def test_format_paths_basic():
    out = _format_paths(["Elon Musk --FOUNDED--> SpaceX", "Tesla --BASED_IN--> California"])
    assert "Context from graph:" in out
    assert "- Elon Musk --FOUNDED--> SpaceX" in out
    assert "- Tesla --BASED_IN--> California" in out


def test_format_context_combines_both():
    docs = [Document(page_content="Hello.", metadata={"source": "a.pdf", "page": 1})]
    paths = ["A --REL--> B"]
    ctx = format_context(docs, paths)
    assert "Context from text:" in ctx
    assert "Context from graph:" in ctx
    assert ctx.index("Context from text:") < ctx.index("Context from graph:")


def test_format_context_handles_empty():
    assert format_context([], []) == "(no context retrieved)"


def test_format_context_text_only():
    docs = [Document(page_content="Hi.", metadata={"source": "x.pdf", "page": 1})]
    out = format_context(docs, [])
    assert "Context from text:" in out
    assert "Context from graph:" not in out


def test_format_context_graph_only():
    out = format_context([], ["A --REL--> B"])
    assert "Context from graph:" in out
    assert "Context from text:" not in out
