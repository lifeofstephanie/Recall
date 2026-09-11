# Gist AI Microservice — Python FastAPI

> **Deployment:** Runs as a **Render web service** (Python runtime). Set `LANCE_DB_URI`,
> `LANCE_API_KEY`, and `LANCE_TABLE_NAME` as environment variables in the Render dashboard.
> `TMDB_API_KEY` is only needed locally for `ingest.py`, not by the running service.
> See `../DEPLOYMENT.md` for the full walkthrough.

The AI brain of the Gist app. Converts text queries into MiniLM vectors (via
lightweight ONNX inference) and runs semantic search against the LanceDB Cloud
movie quotes database.

## Quick Start

```bash
# 1. Create a virtual environment
python -m venv venv
source venv/bin/activate        # Mac/Linux
venv\Scripts\activate           # Windows

# 2. Install dependencies
pip install -r requirements.txt

# 3. Set up environment
cp .env.example .env
# Fill in LANCE_DB_URI, LANCE_API_KEY, TMDB_API_KEY

# 4. Run the ingestion script FIRST (one-time setup)
python ingest.py

# 5. Start the API server
uvicorn main:app --reload --port 8000
```

## Endpoints

| Method | Path      | Description                          |
| ------ | --------- | ------------------------------------ |
| GET    | `/health` | Health check                         |
| POST   | `/search` | Semantic movie search (text → movies)|

### POST /search

**Request:**

```json
{
  "query": "purple guy snapping his fingers",
  "top_k": 5
}
```

**Response:**

```json
{
  "query": "purple guy snapping his fingers",
  "results": [
    { "tmdb_id": 299536, "score": 0.9821 },
    { "tmdb_id": 284054, "score": 0.8743 }
  ]
}
```

## Project Structure

```
gist-ai/
├── main.py                  # FastAPI app + startup lifespan
├── ingest.py                # One-time Kaggle transcripts + TMDb → LanceDB ingestion script
├── Dockerfile               # Hugging Face Spaces deployment
├── requirements.txt
├── app/
│   ├── routes/
│   │   └── search.py        # POST /search endpoint
│   ├── services/
│   │   ├── embedding.py     # MiniLM wrapper (384-dim dense vectors)
│   │   └── lancedb_service.py  # LanceDB Cloud search client
│   └── models/
│       └── schemas.py       # Pydantic request/response models
```

## How the Search Works

```
User query (text)
    ↓
MiniLM model → 384-dim dense vector
    ↓
LanceDB Cloud vector search
    ↓
Deduplicate by tmdb_id (best match per movie)
    ↓
Top 5 TMDb IDs + similarity scores
```

## Deployment (Hugging Face Spaces)

1. Create a new Space on huggingface.co → Docker SDK
2. Push this folder as the Space repository
3. Add your `.env` values as Space Secrets
4. The Dockerfile handles the rest — exposes port 7860
5. Update `AI_SERVICE_URL` in the Node.js gateway `.env` to your Space URL
