FROM python:3.11-slim

WORKDIR /app

# System deps for sentence-transformers and pdfplumber
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpoppler-cpp-dev \
    && rm -rf /var/lib/apt/lists/*

# Python deps first (cache layer)
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# App
COPY neurograph ./neurograph
COPY scripts ./scripts
COPY data ./data

EXPOSE 8000

CMD ["uvicorn", "neurograph.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
