# Deployment Guide

This document walks through pushing the project to GitHub and deploying a public demo on Streamlit Cloud. **Total time: ~15 minutes.**

---

## 1. Final sanity check (before pushing)

```bash
cd ~/Downloads/neurograph
conda activate neurograph
pytest -v   # all tests must pass — no exceptions
```

Expected: `80 passed`.

If anything's red, fix before pushing — broken-test commits look bad on a portfolio repo.

---

## 2. Verify `.gitignore` is doing its job

```bash
git status
```

You should **NOT** see any of these in the staged or modified list:
- `.env`
- `data/chroma/` (contains your local vector index, ~30MB)
- `data/sample_pdfs/*.pdf` (large, regenerable via `download_samples`)
- `eval_results/` (your local eval runs)
- `__pycache__/` directories
- `.venv/`

If any of these show up, the `.gitignore` isn't working. Run:

```bash
cat .gitignore | grep -E "(\.env|chroma|\.pdf|eval_results)"
```

All four should appear. If not, the gitignore got corrupted — copy from this repo's `/.gitignore`.

---

## 3. Commit and push to GitHub

If you haven't created the repo yet:

**Option A — GitHub CLI (cleanest):**
```bash
brew install gh
gh auth login
gh repo create neurograph --public --source=. --push --description "Graph-Augmented RAG over PDFs combining ChromaDB and Neo4j with semantic caching"
```

**Option B — Web UI:**
1. Go to **github.com/new**
2. Repo name: `neurograph`, public, **don't** add README/license/.gitignore
3. Click Create
4. Then in your terminal:
```bash
git branch -M main
git remote add origin https://github.com/<your-username>/neurograph.git
git add .
git commit -m "Phase 1-5 complete: ingestion, dual indexing, hybrid retrieval, cache, eval, UI"
git push -u origin main
```

**Verify on GitHub** that you see:
- Green Actions checkmark (CI passing)
- README rendering with the architecture Mermaid diagram and eval table
- All `docs/images/*.png` showing up

---

## 4. Deploy to Streamlit Cloud

This gives you a public URL like `neurograph.streamlit.app` you can put on your CV.

### 4a. Sign up

1. Go to **streamlit.io/cloud**
2. Sign in with your GitHub account
3. Click **"New app"**

### 4b. Configure the app

- **Repository**: `<your-username>/neurograph`
- **Branch**: `main`
- **Main file path**: `neurograph/ui/app.py`
- **Python version**: 3.11 (default)

### 4c. Add secrets (CRITICAL — without these the app crashes)

Click **"Advanced settings"** → **Secrets**. Paste:

```toml
LLM_PROVIDER = "groq"
GROQ_API_KEY = "gsk_yourActualKey"
GROQ_MODEL = "llama-3.3-70b-versatile"

EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
EMBEDDING_DIM = 384

CHROMA_PERSIST_DIR = "./data/chroma"
CHROMA_COLLECTION = "neurograph"

NEO4J_URI = "neo4j+s://yourInstance.databases.neo4j.io"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "yourActualPassword"

REDIS_URL = "rediss://default:yourPassword@yourHost.upstash.io:6379"
CACHE_THRESHOLD = 0.95

CHUNK_SIZE = 500
CHUNK_OVERLAP = 50
TOP_K_VECTOR = 5
GRAPH_HOPS = 2
```

### 4d. Deploy

Click **Deploy**. First boot takes ~3-5 minutes (installing torch + sentence-transformers). When it's ready, you'll get a URL like:

```
https://neurograph.streamlit.app
```

### 4e. Caveat — ChromaDB on Streamlit Cloud

Streamlit Cloud has an ephemeral filesystem — `data/chroma/` resets on every cold start. Two options:

1. **Acceptable for demo**: when the URL boots cold, run `make ingest` once via the Ingest tab to rebuild the vector index. ~2 min.
2. **Production fix** (roadmap): swap ChromaDB for a hosted vector DB like Pinecone, Weaviate, or pgvector on Supabase. The vector store interface is already abstracted in `neurograph/indexing/vector_store.py` — would be a small refactor.

For your placement demo, option 1 is fine — just re-run ingestion the first time you share the URL.

---

## 5. Update your CV / portfolio

Add a line like:

> **NeuroGraph — Graph-Augmented RAG** ([demo](https://neurograph.streamlit.app) · [code](https://github.com/your-username/neurograph))
> Hybrid vector + knowledge-graph retrieval over PDFs, evaluated with Token Recall, Faithfulness, and Answer Relevance metrics.

Mention specific numbers in the bullet:
- "Built a hybrid retrieval system combining ChromaDB and Neo4j; evaluated on 18 questions × 3 modes"
- "Hybrid retrieval improved Faithfulness from 4.56 to 4.61/5 over vanilla vector RAG"
- "Semantic caching with 0.95 cosine threshold reduces latency from ~10s to ~100ms on repeat queries"

---

## 6. (Optional) Custom domain

If you own a domain, you can point a CNAME at Streamlit Cloud:
- `neurograph.your-name.com` → `your-app.streamlit.app`

Streamlit Cloud's docs cover this under "Custom subdomains" but it requires a paid tier. Skip for placement.

---

## Troubleshooting

**Streamlit Cloud build fails on `torch`**: rare. If it happens, pin `torch==2.4.1` explicitly in `requirements.txt` (we already do).

**App boots but Vector store is empty (0 chunks)**: ChromaDB cold-start issue. Use the Ingest tab to upload a PDF and rebuild the index.

**Graph offline despite Neo4j credentials being correct**: AuraDB free tier auto-pauses after 3 days idle. Resume from the Neo4j console.

**Cache disabled despite Redis URL set**: hit "Refresh status" in the sidebar. The system_status() function caches the connection state per session.

**429 rate limits during demo**: switch to `llama-3.1-8b-instant` model in secrets (separate quota), or just wait 15 minutes for the daily Groq budget to reset.
