"""
GIST - TMDb Data Ingestion Script (FIXED)
=========================================
Debug-safe + production-safe version
"""

import os
import time
import httpx
from dotenv import load_dotenv
from FlagEmbedding import BGEM3FlagModel
from qdrant_client import QdrantClient
from qdrant_client.models import (
    VectorParams,
    SparseVectorParams,
    Distance,
    SparseIndexParams,
    SparseVector,
    PointStruct,
)

load_dotenv()

# ── Config ────────────────────────────────────────────────
TMDB_API_KEY = os.getenv("TMDB_API_KEY")
QDRANT_URL = os.getenv("QDRANT_URL")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
COLLECTION_NAME = os.getenv("QDRANT_COLLECTION_NAME", "movies")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "BAAI/bge-m3")

TMDB_BASE_URL = "https://api.themoviedb.org/3"

BATCH_SIZE = 10
MAX_PAGES = 500
DENSE_VECTOR_SIZE = 1024


# ── TMDb Fetch ───────────────────────────────────────────
def fetch_movies(page: int):
    print(f"\n📡 Fetching page {page}...")

    url = f"{TMDB_BASE_URL}/movie/popular"
    params = {
        "api_key": TMDB_API_KEY,
        "page": page,
        "language": "en-US",
    }

    try:
        response = httpx.get(url, params=params, timeout=httpx.Timeout(20.0))
        print("Status:", response.status_code)

        response.raise_for_status()

        data = response.json()
        results = data.get("results", [])

        print(f"✅ Movies received: {len(results)}")

        return results

    except Exception as e:
        print("❌ TMDb error:", repr(e))
        return []


# ── Text builder ──────────────────────────────────────────
def movie_to_text(movie):
    title = movie.get("title", "")
    overview = movie.get("overview", "")
    year = movie.get("release_date", "")[:4]
    return f"{title} ({year}). {overview}".strip()


# ── Qdrant setup ──────────────────────────────────────────
def setup_collection(client):
    print("\n🧱 Checking Qdrant collection...")

    existing = [c.name for c in client.get_collections().collections]

    if COLLECTION_NAME in existing:
        print(f"✔ Collection '{COLLECTION_NAME}' already exists")
        return

    client.create_collection(
        collection_name=COLLECTION_NAME,
        vectors_config={
            "dense": VectorParams(size=DENSE_VECTOR_SIZE, distance=Distance.COSINE)
        },
        sparse_vectors_config={
            "sparse": SparseVectorParams(index=SparseIndexParams(on_disk=False))
        },
    )

    print(f"✅ Created collection '{COLLECTION_NAME}'")


# ── Embedding + Upload ────────────────────────────────────
def embed_and_upload(client, model, movies, texts):
    print("\n⚡ Embedding batch:", len(texts))

    try:
        output = model.encode(
            texts,
            return_dense=True,
            return_sparse=True,
            return_colbert_vecs=False,
        )
    except Exception as e:
        print("❌ Embedding failed:", repr(e))
        return

    print("✅ Embedding complete")

    points = []

    for i, movie in enumerate(movies):
        dense_vec = output["dense_vecs"][i].tolist()
        sparse_raw = output["lexical_weights"][i]

        sparse_idx = [int(k) for k in sparse_raw.keys()]
        sparse_val = [float(v) for v in sparse_raw.values()]

        points.append(
            PointStruct(
                id=movie["id"],
                vector={
                    "dense": dense_vec,
                    "sparse": SparseVector(
                        indices=sparse_idx,
                        values=sparse_val,
                    ),
                },
                payload={
                    "tmdb_id": movie["id"],
                    "title": movie.get("title"),
                    "poster_path": movie.get("poster_path"),
                    "release_date": movie.get("release_date"),
                },
            )
        )

    print("🚀 Uploading to Qdrant...")

    for attempt in range(3):
        try:
            client.upsert(collection_name=COLLECTION_NAME, points=points)
            print("✅ Upload success")
            return
        except Exception as e:
            print(f"⚠️ Upload attempt {attempt + 1} failed:", repr(e))
            time.sleep(3)

    print("❌ Upload failed permanently for this batch")


# ── Main pipeline ─────────────────────────────────────────
def ingest():
    print("\n🎬 STARTING INGESTION PIPELINE\n")

    model = BGEM3FlagModel(EMBEDDING_MODEL, use_fp16=False)
    print("✅ Model loaded")

    client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY, timeout=60)
    setup_collection(client)

    total_uploaded = 0
    batch_movies = []
    batch_texts = []

    for page in range(1, MAX_PAGES + 1):
        movies = fetch_movies(page)

        if not movies:
            print("⚠️ Empty page skipped")
            continue

        for movie in movies:
            if not movie.get("overview"):
                continue

            batch_movies.append(movie)
            batch_texts.append(movie_to_text(movie))

            print(f"➕ Added: {movie.get('title')}")

            if len(batch_movies) >= BATCH_SIZE:
                print("\n📦 Processing batch...")

                embed_and_upload(client, model, batch_movies, batch_texts)

                total_uploaded += len(batch_movies)
                print(f"📊 Total uploaded so far: {total_uploaded}")

                batch_movies = []
                batch_texts = []

        time.sleep(0.25)

    if batch_movies:
        print("\n📦 Final batch...")
        embed_and_upload(client, model, batch_movies, batch_texts)
        total_uploaded += len(batch_movies)

    print(f"\n🎉 DONE — Total uploaded: {total_uploaded}\n")


# ── Entry point ───────────────────────────────────────────
if __name__ == "__main__":
    ingest()
