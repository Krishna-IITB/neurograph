# Interview Notes — NeuroGraph

> Personal cheat sheet. Not user-facing. Memorize the one-liners.

## 60-second pitch

> *"I built NeuroGraph, a hybrid RAG system that combines semantic vector search with knowledge-graph reasoning over unstructured PDFs. The pipeline ingests PDFs, runs them through an LLM-based cleaning layer, and then builds two parallel indexes — a ChromaDB vector store using MiniLM embeddings, and a Neo4j knowledge graph populated via LLM-extracted entity-relationship triplets with fuzzy entity resolution. At query time, I run vector and graph retrieval in parallel, fuse the contexts, and pass them to Llama-3.1-70B via Groq. I also added a Redis-backed semantic cache with an empirically calibrated 0.95 cosine threshold, and packaged everything in Docker. I evaluated retrieval with Hit Rate and MRR, and generation with Faithfulness and Answer Relevance — hybrid retrieval beat vector-only by X% on Hit Rate."*

## Phase-by-phase one-liners

| Phase | Killer line |
| --- | --- |
| Ingestion | *"I added an LLM cleaning layer because PDF text is messy — garbage in, garbage out."* |
| Chunking | *"500-char chunks with 50-char overlap to preserve semantic continuity across boundaries."* |
| Vector index | *"MiniLM embeddings — 384 dims, the speed-quality sweet spot for retrieval."* |
| Triplet extraction | *"I built the knowledge graph by extracting entity-relationship triplets with an LLM."* |
| Entity resolution | *"Fuzzy matching with Levenshtein distance to unify duplicate entities."* |
| Cypher | *"MERGE not CREATE — idempotent ingestion, no duplicate nodes on re-run."* |
| Hybrid retrieval | *"Vector for similarity, graph for reasoning. Hybrid beats both individually."* |
| Cache | *"Empirically calibrated threshold — 0.95 prevents false-positive cache hits like 'CEO of Tesla' matching 'founder of Tesla'."* |
| Deployment | *"Docker-compose for one-command spin-up, scales horizontally."* |

## Common interview traps

❌ *"What loss function did you use?"*
✅ *"No active loss — this is an inference + retrieval system using pre-trained models. I evaluated with retrieval metrics (Hit Rate, MRR) and generation metrics (Faithfulness, Answer Relevance)."*

❌ *"Did you fine-tune anything?"*
✅ *"No fine-tuning. The novelty is in the retrieval architecture and evaluation, not model training."*

❌ *"Why not just use vector RAG?"*
✅ *"Vector RAG is myopic — it can't answer multi-hop questions. If the answer requires bridging two documents, vector search misses it. Graph traversal handles that explicitly."*

❌ *"Why not just GraphRAG?"*
✅ *"Graph traversal is brittle when entities are misspelled or unmentioned. Vector search catches the long tail. Hybrid wins on both axes."*

## Multi-hop demo questions to memorize

These are the ones to type into the demo when a recruiter is watching — they're where hybrid visibly beats vanilla RAG:

1. *"How is Elon Musk connected to Mars colonization?"*
2. *"Which companies did the founder of SpaceX also start?"*
3. *"Who runs the company that acquired SolarCity?"*

## System-design follow-ups likely to come up

- **Scaling**: ChromaDB is single-node — for >10M chunks, swap to Pinecone/Weaviate/pgvector. Neo4j AuraDB scales vertically; for billions of edges, consider a sharded graph DB.
- **Latency budget**: cache hit ~XXms, cold path ~XXms. Streaming responses cut perceived latency.
- **Failure modes**: triplet extraction hallucination → cross-encoder validation step (roadmap). Cache false positives → monitor hit-rate vs answer-quality drift.
- **Cost**: Groq free tier covers prototyping. Production would need OpenAI/Anthropic for stability + a SLO.
