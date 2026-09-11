"""
GIST - Kaggle & TMDb Ingestion Script (LanceDB Cloud + MiniLM)
===========================================================
Fetches bulk movie transcripts from Kaggle (fayaznoor10/movie-transcripts-59k),
matches them with TMDb IDs via search, embeds chunks of dialogue using MiniLM,
and uploads to LanceDB Cloud.
"""
import os
import sys
import time
import httpx
import lancedb
import pyarrow as pa
from dotenv import load_dotenv
from fastembed import TextEmbedding

# Windows consoles default to cp1252; force UTF-8 so emoji logs don't crash.
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

# Ingestion-only dependency (NOT needed by the deployed service):
#   pip install kagglehub
# Auth: create a Kaggle API token and either export KAGGLE_API_TOKEN=KGAT_...
# or save it to ~/.kaggle/access_token (kagglehub >= 0.4.1 reads it).

load_dotenv()

# ── Config ────────────────────────────────────────────────
TMDB_API_KEY = os.getenv("TMDB_API_KEY")
DB_URI = os.getenv("LANCE_DB_URI")
LANCE_API_KEY = os.getenv("LANCE_API_KEY")
TABLE_NAME = os.getenv("LANCE_TABLE_NAME", "movie_quotes")

EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
TMDB_BASE_URL = "https://api.themoviedb.org/3"
DENSE_VECTOR_SIZE = 384
TRACKER_FILE = "ingested_files.txt"

# Optional knobs (env): INGEST_LIMIT=N stops after N movies (0 = all);
# TMDB_SLEEP is the per-movie delay for the TMDb API (seconds).
INGEST_LIMIT = int(os.getenv("INGEST_LIMIT", "0"))
TMDB_SLEEP = float(os.getenv("TMDB_SLEEP", "0.1"))

# ── Cloud Database Setup ──────────────────────────────────
def setup_database():
    if not DB_URI or not DB_URI.startswith("db://"):
        raise ValueError("❌ ERROR: LANCE_DB_URI must start with 'db://'")
    if not LANCE_API_KEY:
        raise ValueError("❌ ERROR: LANCE_API_KEY is missing.")

    print(f"\n☁️ Connecting to LanceDB Cloud at {DB_URI}...")
    db = lancedb.connect(DB_URI, api_key=LANCE_API_KEY)

    # Schema is updated to remove start/end time since Kaggle transcripts don't have them
    schema = pa.schema(
        [
            pa.field("vector", pa.list_(pa.float32(), DENSE_VECTOR_SIZE)),
            pa.field("tmdb_id", pa.int32()),
            pa.field("title", pa.string()),
            pa.field("quote_text", pa.string()),
        ]
    )

    try:
        table = db.create_table(TABLE_NAME, schema=schema, exist_ok=True)
        print(f"✅ Cloud Table '{TABLE_NAME}' is ready.")
    except Exception as e:
        print(f"❌ Failed to initialize cloud table: {repr(e)}")
        raise e
    return table

# ── TMDb Matcher ──────────────────────────────────────────
def get_tmdb_id(title: str, year: str = None):
    url = f"{TMDB_BASE_URL}/search/movie"
    params = {
        "api_key": TMDB_API_KEY,
        "query": title,
    }
    if year:
        params["primary_release_year"] = year

    try:
        resp = httpx.get(url, params=params, timeout=10.0)
        resp.raise_for_status()
        results = resp.json().get("results", [])
        if results:
            return results[0]["id"], results[0]["title"]
    except Exception as e:
        print(f"   ⚠️ TMDb search failed for {title}: {e}")
    
    return None, None

# ── Bulk Dataset Downloader ───────────────────────────────
def download_dataset():
    dataset_name = "fayaznoor10/movie-transcripts-59k"
    try:
        import kagglehub
    except ImportError:
        print("❌ kagglehub is required for ingestion. Run: pip install kagglehub")
        exit(1)

    print(f"Downloading {dataset_name} via kagglehub (~2.3GB, cached after first run)...")
    try:
        path = kagglehub.dataset_download(dataset_name)
        print(f"✅ Dataset available at {path}")
        return path
    except Exception as e:
        print(f"❌ kagglehub download failed. Check your Kaggle API token: {e}")
        exit(1)


def find_transcript_files(root):
    """Recursively collect .txt transcript files (dataset layout may be nested)."""
    txts = []
    for dirpath, _dirs, files in os.walk(root):
        for f in files:
            if f.endswith(".txt"):
                txts.append(os.path.join(dirpath, f))
    return sorted(txts)

def chunk_dialogue(lines, chunk_size=3):
    """Combines every few lines of dialogue into a single searchable chunk"""
    chunks = []
    for i in range(0, len(lines), chunk_size):
        chunk_text = " ".join(lines[i:i + chunk_size])
        if len(chunk_text.strip()) > 10:
            chunks.append(chunk_text.strip())
    return chunks

# ── Ingestion Engine ──────────────────────────────────────
def ingest():
    print("\n🎬 STARTING BULK INGESTION PIPELINE (Kaggle -> LanceDB Cloud)\n")

    model = TextEmbedding(model_name=EMBEDDING_MODEL)
    print("✅ MiniLM (ONNX) Model loaded successfully")

    table = setup_database()
    # SAMPLE_DIR lets you ingest a handful of pre-downloaded transcripts
    # without pulling the full ~2.3GB dataset.
    download_path = os.getenv("SAMPLE_DIR") or download_dataset()
    if os.getenv("SAMPLE_DIR"):
        print(f"📁 Using sample transcripts from {download_path}")

    processed_movies = 0
    total_chunks = 0

    print("\nProcessing transcripts...")
    
    # Load tracker to know where we stopped
    if os.path.exists(TRACKER_FILE):
        with open(TRACKER_FILE, "r") as f:
            ingested = set(f.read().splitlines())
        print(f"📌 Found tracker file: {len(ingested)} movies already processed. Resuming...")
    else:
        ingested = set()

    files = find_transcript_files(download_path)
    print(f"Found {len(files)} transcript file(s).")

    for file_path in files:
        if INGEST_LIMIT and processed_movies >= INGEST_LIMIT:
            print(f"\n🛑 Reached INGEST_LIMIT={INGEST_LIMIT}. Stopping.")
            break

        filename = os.path.basename(file_path)
        if filename in ingested:
            continue  # Skip locally tracked files instantly

        # Extract title and year from filename (e.g., "The_Dark_Knight_2008.txt")
        name_part = filename.replace(".txt", "")
        parts = name_part.split("_")
        year = parts[-1] if parts[-1].isdigit() and len(parts[-1]) == 4 else None
        raw_title = " ".join(parts[:-1]) if year else " ".join(parts)

        print(f"\n➕ Processing: {raw_title} ({year or 'Unknown'})")

        tmdb_id, official_title = get_tmdb_id(raw_title, year)
        if not tmdb_id:
            print("   Skip: Could not match to TMDb.")
            continue

        # Basic duplicate check (best-effort; may no-op on remote tables)
        try:
            if len(table.to_lance().to_arrow(filter=f"tmdb_id = {tmdb_id}", limit=1)) > 0:
                print("   Skip: Already saved in Cloud Database.")
                continue
        except Exception:
            pass  # Table might be empty on first run

        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = [line.strip() for line in f.readlines() if len(line.strip()) > 10]
        except Exception as e:
            print(f"   ⚠️ Could not read {filename}: {e}")
            continue

        chunks = chunk_dialogue(lines, chunk_size=3)
        if not chunks:
            print("   Skip: No valid dialogue extracted.")
            continue

        print(f"   ⚡ Embedding {len(chunks)} dialogue chunks for: {official_title}")
        try:
            embeddings = list(model.embed(chunks))
        except Exception as e:
            print(f"   ❌ Embedding failed: {e}")
            continue

        data_to_insert = [
            {
                "vector": embeddings[i].tolist(),
                "tmdb_id": int(tmdb_id),
                "title": official_title,
                "quote_text": chunk_text,
            }
            for i, chunk_text in enumerate(chunks)
        ]

        try:
            table.add(data_to_insert)
            total_chunks += len(chunks)
            processed_movies += 1
            with open(TRACKER_FILE, "a") as f:
                f.write(filename + "\n")
            print(f"   ✅ Saved {len(chunks)} chunks.")
        except Exception as e:
            print(f"   ❌ LanceDB Cloud write failed: {e}")

        time.sleep(TMDB_SLEEP)  # Rate limit for TMDb API

    print(f"\n🎉 DONE — Total Movies: {processed_movies} | Total Quotes: {total_chunks}\n")

if __name__ == "__main__":
    ingest()
