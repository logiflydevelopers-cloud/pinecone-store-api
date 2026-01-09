FROM python:3.13-slim

# Install system dependencies for OCR
RUN apt-get update && apt-get install -y \
    poppler-utils \
    tesseract-ocr \
    libgl1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD celery -A app.workers.celery.celery worker \
    -Q pinecone_queue \
    -l info \
    --concurrency=1
