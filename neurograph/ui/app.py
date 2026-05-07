"""NeuroGraph Streamlit UI.

Two tabs:
  - Ask:    natural language Q&A with retrieval-mode toggle and source panel
  - Ingest: drag-and-drop PDF upload that runs the full Phase 1 pipeline

Run:
    streamlit run neurograph/ui/app.py
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

import streamlit as st

from neurograph.cache import semantic_cache
from neurograph.config import settings
from neurograph.generation.llm_client import is_available as llm_available
from neurograph.generation.qa import answer as qa_answer
from neurograph.indexing import graph_store, vector_store
from neurograph.ingestion.pipeline import run_indexing, run_ingestion

# ----- Page config ----------------------------------------------------------

st.set_page_config(
    page_title="NeuroGraph — Graph-Augmented RAG",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    .source-card {
        background: rgba(255,255,255,0.03);
        border-left: 3px solid #4cc9f0;
        padding: 0.6rem 0.9rem;
        margin: 0.4rem 0;
        border-radius: 4px;
        font-size: 0.85rem;
    }
    .graph-path {
        font-family: ui-monospace, SFMono-Regular, monospace;
        font-size: 0.8rem;
        background: rgba(76,201,240,0.08);
        padding: 0.3rem 0.6rem;
        margin: 0.2rem 0;
        border-radius: 3px;
    }
    .badge {
        display: inline-block;
        padding: 0.2rem 0.6rem;
        border-radius: 12px;
        font-size: 0.75rem;
        margin-right: 0.4rem;
    }
    .badge-green { background: rgba(40,180,99,0.2); color: #28b463; }
    .badge-amber { background: rgba(245,176,65,0.2); color: #f5b041; }
    .badge-red   { background: rgba(231,76,60,0.2);  color: #e74c3c; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ----- Session state --------------------------------------------------------

if "history" not in st.session_state:
    st.session_state.history = []  # list of QAResponse for the current session


# ----- Cached resource probes ----------------------------------------------


@st.cache_resource(show_spinner=False)
def system_status() -> dict:
    """One-shot check of every external dependency."""
    status = {
        "llm": False,
        "vector": False,
        "vector_count": 0,
        "graph": False,
        "graph_nodes": 0,
        "graph_rels": 0,
        "cache": False,
        "cache_size": 0,
    }
    status["llm"] = llm_available()
    try:
        status["vector_count"] = vector_store.collection_size()
        status["vector"] = status["vector_count"] > 0
    except Exception:
        pass
    if graph_store.is_configured():
        try:
            s = graph_store.stats()
            status["graph"] = True
            status["graph_nodes"] = s.get("nodes", 0)
            status["graph_rels"] = s.get("rels", 0)
        except Exception:
            pass
    cstats = semantic_cache.stats()
    status["cache"] = cstats["available"]
    status["cache_size"] = cstats["size"]
    return status


def _badge(ok: bool, ok_text: str, bad_text: str = "Not connected") -> str:
    cls = "badge-green" if ok else "badge-red"
    return f'<span class="badge {cls}">{ok_text if ok else bad_text}</span>'


# ----- Sidebar --------------------------------------------------------------

with st.sidebar:
    st.markdown("### 🧠 NeuroGraph")
    st.caption("Graph-Augmented RAG over PDFs")
    st.markdown("---")

    st.markdown("### Retrieval settings")
    mode = st.radio(
        "Mode",
        ["hybrid", "vector", "graph"],
        index=0,
        help="hybrid runs both in parallel and is the recommended default.",
        horizontal=True,
    )
    top_k = st.slider("Vector top-k", 1, 15, settings.top_k_vector, disabled=mode == "graph")
    hops = st.slider("Graph hops", 1, 4, settings.graph_hops, disabled=mode == "vector")
    use_cache = st.toggle("Use semantic cache", value=True)

    st.markdown("---")
    st.markdown("### System status")
    s = system_status()

    st.markdown(_badge(s["llm"], "LLM ready", "LLM down"), unsafe_allow_html=True)
    st.markdown(
        _badge(s["vector"], f"Vector ({s['vector_count']} chunks)", "Vector empty"),
        unsafe_allow_html=True,
    )
    if s["graph"]:
        st.markdown(
            f'<span class="badge badge-green">Graph ({s["graph_nodes"]} nodes, '
            f'{s["graph_rels"]} rels)</span>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(_badge(False, "", "Graph offline"), unsafe_allow_html=True)
    if s["cache"]:
        st.markdown(
            f'<span class="badge badge-green">Cache ({s["cache_size"]} entries)</span>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            '<span class="badge badge-amber">Cache disabled</span>',
            unsafe_allow_html=True,
        )

    st.markdown("---")
    if st.button("🔄 Refresh status", use_container_width=True):
        system_status.clear()
        st.rerun()


# ----- Main -----------------------------------------------------------------

st.title("🧠 NeuroGraph")
st.caption(
    "Hybrid retrieval over PDFs combining **semantic vector search** and "
    "**knowledge-graph reasoning**. Multi-hop questions, citations, and a "
    "semantic cache."
)

tab_ask, tab_ingest = st.tabs(["💬  Ask", "📄  Ingest"])

# -----------------------------------------------------------------------
# Ask tab
# -----------------------------------------------------------------------
with tab_ask:
    EXAMPLES = [
        "What companies has Elon Musk founded?",
        "How is Elon Musk connected to Mars?",
        "When was Tesla founded and by whom?",
        "Who acquired SolarCity and when?",
    ]

    cols = st.columns(len(EXAMPLES))
    chosen_example = None
    for i, ex in enumerate(EXAMPLES):
        if cols[i].button(ex, key=f"ex_{i}", use_container_width=True):
            chosen_example = ex

    question = st.text_input(
        "Ask a question:",
        value=chosen_example or "",
        placeholder="e.g. How is Elon Musk connected to Mars colonization?",
        label_visibility="collapsed",
    )

    submit = st.button("Ask  →", type="primary", use_container_width=False)

    if (submit or chosen_example) and question.strip():
        with st.spinner(f"Running {mode} retrieval + generation..."):
            t0 = time.perf_counter()
            try:
                resp = qa_answer(
                    question.strip(),
                    mode=mode,
                    k=top_k,
                    hops=hops,
                    use_cache=use_cache,
                )
            except Exception as e:
                st.error(f"Error: {e}")
                resp = None
            wall = (time.perf_counter() - t0) * 1000

        if resp:
            st.session_state.history.insert(0, resp)

            # ----- Answer panel -----
            col_ans, col_meta = st.columns([3, 1])
            with col_ans:
                st.markdown("#### Answer")
                st.markdown(resp.answer)
            with col_meta:
                st.metric("Latency", f"{resp.latency_ms:.0f} ms")
                if resp.cache_hit:
                    st.success(f"⚡ Cache hit (cosine={resp.cache_score:.3f})")
                else:
                    st.caption(f"Mode: **{resp.mode}** · Cache miss")
                st.caption(
                    f"Sources: {len(resp.retrieval.chunks)} chunks · "
                    f"{len(resp.retrieval.paths)} graph paths"
                )

            # ----- Sources -----
            if resp.retrieval.chunks or resp.retrieval.paths:
                st.markdown("---")
                col_v, col_g = st.columns(2)

                with col_v:
                    st.markdown(f"##### 📄 Vector sources ({len(resp.retrieval.chunks)})")
                    if not resp.retrieval.chunks:
                        st.caption("_No vector chunks retrieved_")
                    for i, doc in enumerate(resp.retrieval.chunks, 1):
                        src = Path(doc.metadata.get("source", "?")).name
                        page = doc.metadata.get("page", "?")
                        preview = doc.page_content.strip().replace("\n", " ")
                        if len(preview) > 280:
                            preview = preview[:280] + "…"
                        st.markdown(
                            f'<div class="source-card"><b>[{i}] {src} — page {page}</b><br/>'
                            f'{preview}</div>',
                            unsafe_allow_html=True,
                        )

                with col_g:
                    st.markdown(f"##### 🕸️ Graph paths ({len(resp.retrieval.paths)})")
                    if not resp.retrieval.paths:
                        st.caption("_No graph paths retrieved_")
                    for p in resp.retrieval.paths[:15]:
                        st.markdown(f'<div class="graph-path">{p}</div>', unsafe_allow_html=True)
                    if len(resp.retrieval.paths) > 15:
                        st.caption(f"… and {len(resp.retrieval.paths) - 15} more paths")

    elif submit:
        st.warning("Please enter a question.")

    # ----- Recent history -----
    if len(st.session_state.history) > 1:
        st.markdown("---")
        with st.expander(f"🕘 Recent in this session ({len(st.session_state.history) - 1})"):
            for r in st.session_state.history[1:8]:
                badge = "⚡ cached" if r.cache_hit else f"{r.mode}"
                st.markdown(
                    f"**[{badge} · {r.latency_ms:.0f} ms]** {r.answer[:200]}"
                    f"{'…' if len(r.answer) > 200 else ''}"
                )


# -----------------------------------------------------------------------
# Ingest tab
# -----------------------------------------------------------------------
with tab_ingest:
    st.markdown(
        "Drop PDFs here to index them into both ChromaDB (vector) and "
        "Neo4j (knowledge graph). Both indexes are idempotent — re-uploading "
        "a PDF replaces rather than duplicates."
    )

    uploaded = st.file_uploader(
        "Upload one or more PDFs",
        type=["pdf"],
        accept_multiple_files=True,
    )

    col_a, col_b = st.columns(2)
    do_vector = col_a.toggle("Index to vector store (ChromaDB)", value=True)
    do_graph = col_b.toggle("Index to graph (Neo4j, requires LLM)", value=False)

    max_graph_chunks = st.slider(
        "Max chunks for graph indexing (LLM is the bottleneck)",
        50, 1500, 500, 50,
        disabled=not do_graph,
        help="Each chunk costs one LLM call. 500 chunks ≈ 5–10 min on Groq free tier.",
    )

    if uploaded and st.button("Run pipeline", type="primary"):
        # Persist uploads to data/sample_pdfs so the loader can find them
        upload_dir = Path("data/sample_pdfs")
        upload_dir.mkdir(parents=True, exist_ok=True)
        for u in uploaded:
            (upload_dir / u.name).write_bytes(u.read())
        st.info(f"Saved {len(uploaded)} file(s) to {upload_dir}/")

        with st.status("Phase 1A — loading + chunking + cleaning...", expanded=True) as s1:
            chunks = run_ingestion(upload_dir, use_llm_clean=False)
            s1.update(label=f"Phase 1A complete: {len(chunks)} chunks", state="complete")

        with st.status("Phase 1B — indexing...", expanded=True) as s2:
            summary = run_indexing(
                chunks,
                do_vector=do_vector,
                do_graph=do_graph,
                max_chunks_for_graph=max_graph_chunks if do_graph else None,
            )
            s2.update(
                label=(
                    f"Phase 1B complete: {summary['vectors']} vectors, "
                    f"{summary['graph_nodes']} graph nodes, "
                    f"{summary['graph_rels']} graph relationships"
                ),
                state="complete",
            )

        # Force the sidebar status to refresh
        system_status.clear()
        st.success("Indexing complete. Switch to the **Ask** tab to query.")

    if not uploaded:
        st.caption(
            "_No files uploaded yet. The bundled sample PDFs are already indexed "
            "if you ran `make ingest` from the CLI._"
        )
