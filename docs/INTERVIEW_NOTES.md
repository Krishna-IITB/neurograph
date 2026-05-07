# Interview Notes — NeuroGraph

> Personal cheat sheet. Not user-facing. Memorize the one-liners.

---

## 60-second pitch

> *"NeuroGraph is a Graph-Augmented RAG system that combines semantic vector search with knowledge-graph reasoning over PDFs. The pipeline ingests PDFs, runs them through an LLM cleaning layer, and builds two parallel indexes — a ChromaDB vector store with MiniLM embeddings, and a Neo4j knowledge graph populated via LLM-extracted (head, relation, tail) triplets with fuzzy entity resolution. At query time, vector and graph retrievals run in parallel and the contexts are fused before Llama-3.3-70B generates the answer. There's also a Redis-backed semantic cache with an empirically calibrated 0.95 cosine threshold for paraphrased queries. I evaluated 18 questions × 3 retrieval modes × 4 metrics. Vector RAG was already 100% on Token Recall for Wikipedia-style content; hybrid edged it on Faithfulness from 4.56 to 4.61 by acting as a verification signal. Total: 80 unit tests, 626-node graph, deployed on Streamlit Cloud."*

---

## Real eval numbers (memorize these)

| Mode | Recall | Faith. | Relev. | Correct. | Latency |
| --- | --- | --- | --- | --- | --- |
| **Vector** | 1.000 | 4.56 | 4.11 | 3.89 | 8.1 s |
| **Graph** | 0.333 | 2.94 | 2.00 | 1.72 | 6.6 s |
| **Hybrid** | 1.000 | **4.61** | 3.94 | 3.83 | 13.6 s |

**The interview-grade interpretation:**

> *"Vector RAG was very strong on Wikipedia content — single-hop queries don't need graph reasoning. Hybrid edged vector specifically on Faithfulness (4.61 vs 4.56), because graph paths act as a cross-verification signal that keeps the LLM grounded. The cost is real: hybrid takes 1.7× longer because of parallel retrieval plus an extra LLM call for entity extraction. For production, I'd route single-hop questions to vector by default and escalate to hybrid only for multi-hop or cross-document reasoning. Graph alone is weakest at 33% Recall — its value is as augmentation, not replacement."*

This answer wins because it shows engineering judgment. Most candidates pitch their system; few articulate when their system *doesn't* win.

---

## Phase-by-phase one-liners

| Phase | Killer line |
| --- | --- |
| Ingestion | *"I added a regex + LLM cleaning layer because PDF text is messy — garbage in, garbage out."* |
| Chunking | *"500-char chunks with 50-char overlap to preserve semantic continuity across boundaries."* |
| Vector index | *"MiniLM embeddings — 384 dims, the speed-quality sweet spot, runs locally on M-series with Metal."* |
| Triplet extraction | *"LLM extracts (head, relation, tail) triplets with strict JSON schema and defensive parsing."* |
| Entity resolution | *"Fuzzy matching with Levenshtein distance unifies duplicate entities (Tesla / Tesla Inc / Tesla Motors)."* |
| Cypher | *"`MERGE` not `CREATE` — idempotent ingestion, no duplicate nodes on re-run."* |
| Hybrid retrieval | *"Vector and graph run concurrently in a thread pool, contexts fused before generation."* |
| Cache | *"0.95 cosine threshold — empirically calibrated. Below that, false positives. Above, almost no hits."* |
| Eval | *"4 metrics × 3 modes on 18 hand-curated questions, Token Recall + LLM-as-judge."* |
| Deployment | *"Docker-compose for one-command spin-up; Streamlit Cloud for the public demo URL."* |

---

## Common interview traps

❌ *"What loss function did you use?"*
✅ *"No active loss — this is an inference + retrieval system using pre-trained models. Quality is measured via retrieval + generation metrics: Token Recall, Faithfulness, Answer Relevance, Correctness — RAGAS-style."*

❌ *"Did you fine-tune anything?"*
✅ *"No fine-tuning. The novelty is in the retrieval architecture and rigorous evaluation, not model training. Adding fine-tuning would be a future direction — particularly for the entity-extraction step."*

❌ *"Why not just use vector RAG?"*
✅ *"Vector RAG is myopic — it can't answer multi-hop questions. If the answer requires bridging two documents, vector misses it. Graph traversal handles that explicitly. My eval also shows hybrid edges vector on Faithfulness (4.61 vs 4.56) by acting as a verification signal."*

❌ *"Why not just GraphRAG?"*
✅ *"Graph traversal is brittle when entities are misspelled or unmentioned. My eval shows graph alone gets 33% Recall — way below vector's 100%. Vector catches the long tail, graph adds reasoning. Hybrid wins on both."*

❌ *"What's the biggest weakness?"*
✅ *"Wikipedia PDFs have huge References sections that crowd out body content during retrieval — I documented this and have reference-stripping on the roadmap. Also, hybrid latency is 2× vector, so production should route smartly: vector for single-hop, hybrid for multi-hop."*

❌ *"How would you scale this?"*
✅ *"ChromaDB is single-node — for >10M chunks, swap to Pinecone or pgvector. Neo4j AuraDB scales vertically; for billions of edges, consider a sharded graph DB. Add streaming responses to cut perceived latency. Add a cross-encoder reranker for higher precision on top-k."*

---

## Multi-hop demo questions to memorize

These visibly demonstrate hybrid > vector when typed live:

1. *"How is Elon Musk connected to Mars colonization?"*
2. *"Which companies did the founder of SpaceX also start?"*
3. *"What does the company that Elon Musk leads in California make?"*

For your screen-share demo:
- Click these in the Streamlit UI
- Show the hybrid mode answer
- Pull up the graph paths and vector chunks side-by-side
- Mention: *"Notice how the graph paths trace the entity chain explicitly while the chunks ground specific facts."*

---

## System-design follow-ups

- **Latency budget**: cache hit ~100ms, vector cold ~8s, hybrid cold ~14s. Streaming responses cut perceived latency. Smart routing avoids hybrid for single-hop questions.
- **Failure modes**: triplet extraction hallucination → cross-encoder validation step (roadmap). Cache false positives → monitor hit-rate vs answer-quality drift.
- **Cost**: Groq free tier (Llama-3.3-70B) covers prototyping at zero cost. Production would need OpenAI or Anthropic for stability + a SLO.
- **Observability**: roadmap item — OpenTelemetry tracing through the retrieve → generate → cache pipeline for production debugging.

---

## Things to *not* claim

- ❌ "My system is better than RAGAS." (RAGAS is a metric library, not a system. Don't compare apples to oranges.)
- ❌ "Hybrid always wins." (Numbers say otherwise — be honest about Relevance and Latency.)
- ❌ "It's production-ready." (It's a portfolio project. ChromaDB is single-node, no auth on FastAPI, no observability. Be clear about what's prototype.)
- ❌ Vague hand-waving when asked about numbers. *Always* refer to your real eval table.
