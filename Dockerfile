FROM python:3.11-slim

WORKDIR /app

# System deps for sentence-transformers and chromadb
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libgomp1 \
 && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# data/ and logs/ should be mounted as volumes in production
RUN mkdir -p data/corpus data/memory data/vectordb logs

EXPOSE 8000

CMD ["uvicorn", "lios.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
