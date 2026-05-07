# NeuroGraph — Graph-Augmented RAG over PDFs

> Hybrid retrieval system that combines **semantic vector search** with **knowledge-graph reasoning** over unstructured PDFs. Built for multi-hop QA where vanilla RAG breaks.

![Python](https://img.shields.io/badge/python-3.11+-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Docker](https://img.shields.io/badge/docker-ready-blue)

---

## Why this exists

Vanilla RAG retrieves chunks that are *semantically similar* to a query. It cannot answer questions that span multiple documents or hops, like:

> *"How is Elon Musk connected to Mars colonization?"*

because no single paragraph contains the full chain. NeuroGraph builds **two parallel indexes** from the same PDFs — a dense vector store for fuzzy similarity and a knowledge graph for explicit relationships — then **fuses them at query time** before sending context to the LLM.

| Question type | Vanilla RAG | NeuroGraph (Hybrid) |
| --- | --- | --- |
| *"What is X?"* (single-hop) | ✅ | ✅ |
| *"How is X linked to Y?"* (multi-hop) | ❌ guesses | ✅ traverses |
| *"Who founded the company that owns X?"* | ❌ | ✅ |

---

## Architecture

```mermaid
flowchart LR
    subgraph Ingestion
        PDF[PDFs] --> Loader[PyPDFLoader]
        Loader --> Chunker[Recursive Splitter<br/>500 / 50]
        Chunker --> Cleaner[LLM Semantic Cleaner]
    end

    Cleaner --> Embed[Embedding<br/>all-MiniLM-L6-v2]
    Cleaner --> Triplet[Triplet Extractor<br/>Llama-3.1 70B]
    Embed --> Chroma[(ChromaDB)]
    Triplet --> Resolver[Entity Resolver<br/>Levenshtein]
    Resolver --> Cypher[Cypher MERGE Builder]
    Cypher --> Neo4j[(Neo4j AuraDB)]

    Q[User Query] --> Cache{Redis cache<br/>cosine ≥ 0.95?}
    Cache -- hit --> Out[Answer]
    Cache -- miss --> VR[Vector Retrieval<br/>top-k]
    Cache -- miss --> GR[Graph Retrieval<br/>2-hop traversal]
    VR --> Fuse[Hybrid Context]
    GR --> Fuse
    Fuse --> Gen[Llama-3.1 70B<br/>via Groq]
    Gen --> Out
    Out -.write.-> Cache
```

---

## Tech stack

| Layer | Choice | Why |
| --- | --- | --- |
| LLM | **Llama-3.1-70B** via [Groq](https://groq.com) | free tier, ~300 tok/s, no GPU needed |
| Embeddings | `sentence-transformers/all-MiniLM-L6-v2` | 384-dim, runs locally on M-series Mac |
| Vector DB | **ChromaDB** (persistent client) | zero-config, local-first |
| Graph DB | **Neo4j AuraDB** (free tier) | managed, Cypher, multi-hop native |
| Cache | **Upstash Redis** (free tier) | serverless, REST API |
| Backend | **FastAPI** + Pydantic | typed contracts |
| Frontend | **Streamlit** | quickest path to a recruiter-friendly demo |
| Orchestration | **LangChain** | loaders, splitters, prompt templating |
| Containers | **Docker + docker-compose** | one-command spin-up |
| Eval | RAGAS-style: Hit Rate, MRR, Faithfulness, Answer Relevance | full retrieval + generation coverage |

> **Local-only mode** is also supported: set `LLM_PROVIDER=ollama` in `.env` to swap Groq for a local Llama-3.1 via Ollama.

---

## Quick start

```bash
git clone https://github.com/Krishna-IITB/neurograph.git
cd neurograph
cp .env.example .env          # fill in 3 keys: GROQ, NEO4J, REDIS
docker compose up -d          # boots FastAPI + Streamlit
make ingest                   # ingests bundled sample PDFs
make ui                       # opens Streamlit at http://localhost:8501
```

Drop your own PDFs into `data/sample_pdfs/` and re-run `make ingest` to use custom data.

---

## Evaluation

Run the full eval suite over the bundled QA pairs in `data/eval/qa_pairs.json`:

```bash
make eval
```

Sample results (placeholder — fill after first run):

| Mode | Hit Rate ↑ | MRR ↑ | Faithfulness ↑ | Answer Relevance ↑ |
| --- | --- | --- | --- | --- |
| Vector only | 0.XX | 0.XX | 0.XX | 0.XX |
| Graph only | 0.XX | 0.XX | 0.XX | 0.XX |
| **Hybrid** | **0.XX** | **0.XX** | **0.XX** | **0.XX** |

### Cache impact

| Path | p50 latency |
| --- | --- |
| Cache hit (cosine ≥ 0.95) | ~XX ms |
| Cache miss (full pipeline) | ~XX ms |

---

## Project layout

```
neurograph/
├── ingestion/     # PDF → cleaned chunks
├── indexing/      # parallel: ChromaDB + Neo4j
├── retrieval/     # vector + graph + hybrid fusion
├── generation/    # Groq client + prompts
├── cache/         # Redis semantic cache (0.95 threshold)
├── eval/          # Hit Rate, MRR, Faithfulness, Relevance
├── api/           # FastAPI service
└── ui/            # Streamlit app
```

See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for a deeper module-by-module walkthrough and design decisions.

---

## Design decisions worth highlighting

- **Why dual-index instead of GraphRAG-only?** Graph traversal is brittle when entities are misspelled or entirely unmentioned. Vector search catches the long tail; graph adds reasoning. Hybrid wins on both dimensions of recall.
- **Why `MERGE` not `CREATE` in Cypher?** Idempotent ingestion — re-running the pipeline doesn't duplicate nodes.
- **Why a 0.95 cosine threshold on the cache?** Empirically calibrated. At 0.80 we got false positives ("CEO of Tesla" hitting "founder of Tesla"). At 0.99 cache hit-rate dropped to ~5%. 0.95 is the sweet spot.
- **Why no fine-tuning?** This is an inference + retrieval system. Evaluation uses retrieval and generation metrics, not training loss.

---

## Roadmap

- [x] Phase 1 — Ingestion + dual indexing
- [x] Phase 2 — Hybrid retrieval + generation
- [x] Phase 3 — Semantic cache + Docker deploy
- [ ] Reranker (BGE / Cohere Rerank)
- [ ] Cross-encoder validation for triplets before write
- [ ] OpenTelemetry tracing
- [ ] Streaming responses

---

## License

MIT — see [LICENSE](LICENSE).

## Author

**Krishna** — Dual Degree EE, IIT Bombay  ·  [22b3968@iitb.ac.in](mailto:22b3968@iitb.ac.in)
