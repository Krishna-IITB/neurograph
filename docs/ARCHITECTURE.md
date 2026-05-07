# Architecture

This document goes one level deeper than the README — module-by-module design choices and the tradeoffs behind them.

## High-level dataflow

NeuroGraph runs in two modes:

1. **Ingestion** (offline, run once per dataset): PDFs → cleaned chunks → vector index + knowledge graph.
2. **Query** (real-time, every request): question → cache check → hybrid retrieval → LLM generation → cache write.

## Phase 1: Ingestion

### Loader (`ingestion/loader.py`)
Wraps LangChain's `PyPDFLoader`. Returns one `Document` per page so we keep page metadata for citation in the UI later.

### Chunker (`ingestion/chunker.py`)
`RecursiveCharacterTextSplitter` with **500-char chunks, 50-char overlap**. The splitter respects paragraph and sentence boundaries before falling back to characters. Overlap preserves semantic continuity so a key fact split across chunks still appears in at least one complete chunk.

### Cleaner (`ingestion/cleaner.py`)
Each chunk is sent through Llama-3.1 with a strict prompt: *clean OCR errors, fix broken words, do not add information*. This is the most expensive step in ingestion — runs ~1 LLM call per chunk. Skipped via `--no-clean` for fast iteration.

## Phase 1 (continued): Dual indexing

Both indexes are built **in parallel** from the same cleaned chunks.

### Vector path (`indexing/vector_store.py`)
- Embedding: `all-MiniLM-L6-v2` (384-dim). Chosen for the speed/quality sweet spot — runs locally on M-series with Metal acceleration, ~2ms per chunk.
- Storage: ChromaDB persistent client. Survives restarts via `data/chroma/`.
- Metadata: source file, page number, chunk index — used for citation.

### Graph path (`indexing/triplet_extractor.py` → `entity_resolver.py` → `cypher_builder.py` → `graph_store.py`)

1. **Triplet extraction** — strict-JSON LLM call asking for `(head, relation, tail)` triplets. Relations are normalized to `UPPERCASE_SNAKE_CASE`.
2. **Entity resolution** — fuzzy match (rapidfuzz, Levenshtein-based) every new entity against existing ones. Threshold 90 of 100. Prevents `Tesla` / `Tesla Inc` / `Tesla Motors` from becoming three separate nodes.
3. **Cypher building** — every triplet becomes a `MERGE` query. `MERGE` is idempotent (create if missing, reuse if exists), so re-ingesting the same PDF doesn't pollute the graph.
4. **Storage** — Neo4j AuraDB free tier. All triplets for a single batch are written in one transaction.

## Phase 2: Retrieval + Generation

### Vector retriever (`retrieval/vector_retriever.py`)
Top-`k` cosine similarity. `k=5` by default — empirically enough context for the 70B model without diluting signal.

### Graph retriever (`retrieval/graph_retriever.py`)
1. Extract entities from the user's question (LLM call).
2. For each entity, run a Cypher query with `*1..N` hops (default `N=2`).
3. Convert paths to natural language: `Elon Musk --FOUNDED--> SpaceX --TARGETS--> Mars`.

### Hybrid fusion (`retrieval/hybrid.py`)
Both retrievers run concurrently. Their outputs are concatenated under labeled headers in the final prompt. The LLM sees both signals and decides which to lean on per-question.

### Generation (`generation/llm_client.py`)
Single client class abstracts over Groq and Ollama. The same call signature works for both. Temperature pinned at 0.0 for determinism in eval runs.

## Phase 3: Caching + Deployment

### Semantic cache (`cache/semantic_cache.py`)
- On query: embed → search Redis for nearest stored embedding → if cosine ≥ **0.95**, return cached answer; else miss.
- On miss: run pipeline, write `(embedding, answer)` to Redis.
- Threshold of 0.95 was calibrated empirically — `0.80` produced false positives, `0.99` killed hit-rate. 0.95 is the production sweet spot.

### Containerization
`docker-compose` boots two services: FastAPI and Streamlit. Both share the same image (just different `command`). Volume-mounts `./data` so ChromaDB persistence survives `docker compose down`.

## Why no training loss?

This is an **inference + retrieval system**, not a training pipeline. We use pre-trained models for embeddings and generation, so there is no loss function in the traditional sense. Quality is measured via:

- **Retrieval metrics** — Hit Rate, MRR
- **Generation metrics** — Faithfulness, Answer Relevance

See `eval/` for implementations.
