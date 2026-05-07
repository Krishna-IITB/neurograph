.PHONY: help install ingest query api ui eval test lint format clean docker-up docker-down

help:  ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

install:  ## Install dependencies
	pip install -r requirements.txt

ingest:  ## Ingest PDFs from data/sample_pdfs/
	python -m scripts.ingest data/sample_pdfs

query:  ## CLI query (usage: make query Q="who founded Tesla")
	python -m scripts.query "$(Q)"

api:  ## Run FastAPI dev server
	uvicorn neurograph.api.main:app --host 0.0.0.0 --port 8000 --reload

ui:  ## Run Streamlit
	streamlit run neurograph/ui/app.py --server.port 8501

eval:  ## Run full eval suite (Hit Rate, MRR, Faithfulness, Relevance)
	python -m scripts.run_eval

test:  ## Run pytest
	pytest -v

lint:  ## Run ruff
	ruff check neurograph tests scripts

format:  ## Format with ruff
	ruff format neurograph tests scripts

clean:  ## Remove caches and build artifacts
	rm -rf .pytest_cache .ruff_cache .mypy_cache build dist *.egg-info
	find . -type d -name __pycache__ -exec rm -rf {} +

docker-up:  ## Spin up the full stack
	docker compose up -d

docker-down:  ## Tear down the stack
	docker compose down
