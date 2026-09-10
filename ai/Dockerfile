FROM python:3.10-slim

WORKDIR /app

# Install Python dependencies first (better layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Bake the MiniLM model into the image so cold starts are fast and the
# container never needs to download it at runtime. HF_HOME points at a
# world-readable cache directory that works whether the Space runs the
# container as root or as the default uid-1000 user.
ENV HF_HOME=/app/hf_cache
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')" \
    && chmod -R a+rX /app/hf_cache

# Copy source code (see .dockerignore — venv, .env, data are excluded)
COPY . .

# Hugging Face Spaces routes public HTTPS traffic to this port
EXPOSE 7860

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "7860"]
