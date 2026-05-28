# Gist AI Microservice — Python FastAPI

The AI brain of the Gist app. Converts text queries into BGE-M3 vectors
and runs hybrid semantic search against the Qdrant movie database.

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
# Fill in QDRANT_URL, QDRANT_API_KEY, TMDB_API_KEY

# 4. Run the ingestion script FIRST (one-time setup)
python ingest.py

# 5. Start the API server
uvicorn main:app --reload --port 8000
```

## Endpoints

| Method | Path      | Description             |
| ------ | --------- | ----------------------- |
| GET    | `/health` | Health check            |
| POST   | `/search` | Run hybrid movie search |

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
├── ingest.py                # One-time TMDb → Qdrant ingestion script
├── Dockerfile               # Hugging Face Spaces deployment
├── requirements.txt
├── app/
│   ├── routes/
│   │   └── search.py        # POST /search endpoint
│   ├── services/
│   │   ├── embedding.py     # BGE-M3 wrapper (dense + sparse)
│   │   └── qdrant.py        # Qdrant hybrid search client
│   └── models/
│       └── schemas.py       # Pydantic request/response models
```

## How the Search Works

```
User query
    ↓
BGE-M3 model → Dense vector (semantic meaning)
             → Sparse vector (exact keywords)
    ↓
Qdrant Hybrid Search
  ├── Dense leg  → top 15 by cosine similarity
  └── Sparse leg → top 15 by keyword match
    ↓
Reciprocal Rank Fusion (RRF) → merges both lists
    ↓
Top 5 TMDb IDs + confidence scores
```

## Deployment (Hugging Face Spaces)

1. Create a new Space on huggingface.co → Docker SDK
2. Push this folder as the Space repository
3. Add your `.env` values as Space Secrets
4. The Dockerfile handles the rest — exposes port 7860
5. Update `AI_SERVICE_URL` in the Node.js gateway `.env` to your Space URL
