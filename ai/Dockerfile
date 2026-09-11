FROM python:3.11-slim

WORKDIR /app

# Install Python dependencies first (better layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Pre-download the ONNX MiniLM model so cold starts don't wait on a download.
# fastembed + ONNX Runtime is lightweight (no PyTorch) and runs well under 512MB.
RUN python -c "from fastembed import TextEmbedding; TextEmbedding(model_name='sentence-transformers/all-MiniLM-L6-v2')"

# Copy source code (see .dockerignore — venv, .env, data are excluded)
COPY . .

# Render (and most PaaS) inject the port via $PORT; default to 8000 locally.
ENV PORT=8000
EXPOSE 8000

CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]
