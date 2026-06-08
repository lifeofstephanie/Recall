"""
GIST - TMDb & SubDL Ingestion Script (LanceDB Cloud + MiniLM) - Optimized
===========================================================
Fetches classic blockbuster English movies, checks for duplicates,
extracts subtitles in-memory, embeds quotes, and uploads to LanceDB Cloud.
"""

import os
import time
import httpx
import lancedb
import zipfile
import io
import re
import pyarrow as pa
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer

load_dotenv()

# ── Config ────────────────────────────────────────────────
TMDB_API_KEY = os.getenv("TMDB_API_KEY")
SUBDL_API_KEY = os.getenv("SUBDL_API_KEY")

# Cloud Database credentials
DB_URI = os.getenv("LANCE_DB_URI")
LANCE_API_KEY = os.getenv("LANCE_API_KEY")
TABLE_NAME = os.getenv("LANCE_TABLE_NAME", "movie_quotes")

EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
TMDB_BASE_URL = "https://api.themoviedb.org/3"
SUBDL_BASE_URL = "https://api.subdl.com/api/v1/subtitles"

MAX_PAGES = 5  # 5 pages * 20 movies = 100 movies for testing
DENSE_VECTOR_SIZE = 384


# ── Cloud Database Setup ──────────────────────────────────
def setup_database():
    if not DB_URI or not DB_URI.startswith("db://"):
        raise ValueError(
            "❌ ERROR: LANCE_DB_URI must be a valid cloud URI starting with 'db://'"
        )
    if not LANCE_API_KEY:
        raise ValueError(
            "❌ ERROR: LANCE_API_KEY is missing from your environment variables."
        )

    print(f"\n☁️ Connecting to LanceDB Cloud at {DB_URI}...")

    # Establish a connection to the serverless remote database
    db = lancedb.connect(DB_URI, api_key=LANCE_API_KEY)

    # Define the exact schema for the table
    schema = pa.schema(
        [
            pa.field("vector", pa.list_(pa.float32(), DENSE_VECTOR_SIZE)),
            pa.field("tmdb_id", pa.int32()),
            pa.field("title", pa.string()),
            pa.field("quote_text", pa.string()),
            pa.field("start_time", pa.string()),
            pa.field("end_time", pa.string()),
        ]
    )

    try:
        # Open table if it exists, or create it using the specified schema
        table = db.create_table(TABLE_NAME, schema=schema, exist_ok=True)
        print(f"✅ Cloud Table '{TABLE_NAME}' is ready.")
    except Exception as e:
        print(f"❌ Failed to initialize cloud table: {repr(e)}")
        raise e

    return table


# ── Duplicate Check ───────────────────────────────────────
def movie_exists(table, tmdb_id):
    """Checks if the database already contains quotes for this movie."""
    try:
        # Ask LanceDB for just 1 row matching this exact TMDB ID
        results = table.search().where(f"tmdb_id = {tmdb_id}").limit(1).to_list()
        return len(results) > 0
    except Exception:
        # If the table is completely empty, LanceDB might throw an error on search
        return False


# ── TMDb Fetch (Optimized for Classic Blockbusters) ───────
def fetch_movies(page: int):
    print(f"\n📡 Fetching TMDb page {page}...")
    try:
        response = httpx.get(
            f"{TMDB_BASE_URL}/discover/movie",
            params={
                "api_key": TMDB_API_KEY,
                "page": page,
                "with_original_language": "en",  # Filters out non-English origin films
                "sort_by": "vote_count.desc",  # OPTIMIZED: Grabs the most voted/famous movies ever
            },
            timeout=20.0,
        )
        response.raise_for_status()
        results = response.json().get("results", [])
        return results
    except Exception as e:
        print("❌ TMDb error:", repr(e))
        return []


# ── SubDL Fetch & Parse (Robust Matching) ──────────────────
def fetch_and_parse_subtitles(tmdb_id):
    """Hits SubDL, downloads the ZIP, extracts the SRT, and parses quotes."""
    try:
        # 1. Ask SubDL for subtitle links for this specific movie
        response = httpx.get(
            SUBDL_BASE_URL,
            params={"api_key": SUBDL_API_KEY, "tmdb_id": tmdb_id},
            timeout=20.0,
        )
        response.raise_for_status()
        data = response.json()

        if not data.get("subtitles"):
            return []

        # 2. Find the first English subtitle track (Case-Insensitive Match)
        english_subs = []
        for s in data["subtitles"]:
            lang = s.get("language", "").lower()
            if "english" in lang or lang == "en":
                english_subs.append(s)

        if not english_subs:
            return []

        target_sub = english_subs[0]
        download_url = target_sub.get("url")
        if download_url.startswith("/"):
            download_url = "https://dl.subdl.com" + download_url

        # 3. Download the ZIP file into memory
        zip_response = httpx.get(download_url, timeout=30.0)
        zip_response.raise_for_status()

        # 4. Extract the SRT file from the in-memory ZIP
        with zipfile.ZipFile(io.BytesIO(zip_response.content)) as z:
            srt_filename = next(
                (name for name in z.namelist() if name.endswith(".srt")), None
            )
            if not srt_filename:
                return []

            srt_bytes = z.read(srt_filename)
            try:
                srt_text = srt_bytes.decode("utf-8")
            except UnicodeDecodeError:
                srt_text = srt_bytes.decode("latin-1")  # Fallback for older encodings

        # 5. Parse raw SRT text into clean semantic chunks
        parsed_quotes = []
        pattern = re.compile(
            r"(\d{2}:\d{2}:\d{2},\d{3}) --> (\d{2}:\d{2}:\d{2},\d{3})\n(.*?)(?=\n\n|\Z)",
            re.DOTALL,
        )
        matches = pattern.findall(srt_text.replace("\r", ""))

        for start, end, raw_text in matches:
            clean_text = re.sub(r"<[^>]+>", "", raw_text).replace("\n", " ").strip()
            if clean_text:
                parsed_quotes.append({"start": start, "end": end, "text": clean_text})

        return parsed_quotes

    except Exception as e:
        print(f"   ⚠️ Subtitle fetch failed for {tmdb_id}: {repr(e)}")
        return []


# ── Embedding + Cloud Upload ──────────────────────────────
def embed_and_upload_movie(table, model, movie, quotes):
    if not quotes:
        return 0

    print(f"   ⚡ Embedding {len(quotes)} quotes for: {movie.get('title')}")

    texts = [q["text"] for q in quotes]

    try:
        # Generate the 384-dimension vectors locally
        embeddings = model.encode(texts)
    except Exception as e:
        print("   ❌ Embedding failed:", repr(e))
        return 0

    # Format the rows to match the LanceDB schema
    data_to_insert = []
    for i, quote in enumerate(quotes):
        data_to_insert.append(
            {
                "vector": embeddings[i].tolist(),
                "tmdb_id": movie["id"],
                "title": movie.get("title", ""),
                "quote_text": quote["text"],
                "start_time": quote["start"],
                "end_time": quote["end"],
            }
        )

    try:
        # Stream the formatted rows straight over the web to your cloud database instance
        table.add(data_to_insert)
        return len(quotes)
    except Exception as e:
        print("   ❌ LanceDB Cloud write failed:", repr(e))
        return 0


# ── Main pipeline ─────────────────────────────────────────
def ingest():
    print("\n🎬 STARTING LANCE_DB CLOUD INGESTION PIPELINE\n")

    model = SentenceTransformer(EMBEDDING_MODEL)
    print("✅ MiniLM Model loaded successfully")

    # Connect to remote cloud instance
    table = setup_database()

    total_movies = 0
    total_quotes = 0

    for page in range(1, MAX_PAGES + 1):
        movies = fetch_movies(page)

        if not movies:
            continue

        for movie in movies:
            print(f"\n➕ Processing: {movie.get('title')} ({movie['id']})")

            # 🛑 NEW: Check if the database already has this movie before doing anything
            if movie_exists(table, movie["id"]):
                print("   ⏭️ Skipped (Already saved in Cloud Database)")
                continue

            # Fetch and parse the subtitles for this movie
            quotes = fetch_and_parse_subtitles(movie["id"])

            if quotes:
                # Embed the quotes and write them to the cloud table
                quotes_inserted = embed_and_upload_movie(table, model, movie, quotes)
                total_quotes += quotes_inserted
                total_movies += 1
            else:
                print("   ⏭️ Skipped (No English subtitles found)")

            # Throttling rate limit safety buffer
            time.sleep(1.5)

        print(
            f"\n📊 Progress: {total_movies} movies and {total_quotes} quotes successfully pushed to the Cloud."
        )

    print(
        f"\n🎉 DONE — Total Movies Uploaded: {total_movies} | Total Quotes Stored: {total_quotes}\n"
    )


if __name__ == "__main__":
    ingest()
