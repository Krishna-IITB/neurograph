"""Streamlit demo for NeuroGraph.

Two tabs:
  1. Ask — user types a question, sees retrieval mode toggle + answer + sources.
  2. Ingest — drag-and-drop PDF upload.
"""

import streamlit as st

st.set_page_config(page_title="NeuroGraph", page_icon="🧠", layout="wide")

st.title("🧠 NeuroGraph — Graph-Augmented RAG")
st.caption("Hybrid retrieval over PDFs · ChromaDB + Neo4j + Redis cache")

tab_ask, tab_ingest = st.tabs(["Ask", "Ingest"])

with tab_ask:
    st.info("Phase 2 — wire this up after retrieval is implemented.")

with tab_ingest:
    st.info("Phase 1 — wire this up after ingestion is implemented.")
