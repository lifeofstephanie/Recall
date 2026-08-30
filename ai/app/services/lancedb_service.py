import os
import lancedb


class LanceDBService:
    """
    Handles all LanceDB Cloud interactions for movie quote search.

    The movie_quotes table stores one vector per subtitle chunk. A single
    movie may have hundreds of chunks, so search results are deduplicated
    by tmdb_id — keeping only the closest match per movie.
    """

    def __init__(self):
        db_uri = os.getenv("LANCE_DB_URI")
        api_key = os.getenv("LANCE_API_KEY")
        table_name = os.getenv("LANCE_TABLE_NAME", "movie_quotes")

        if not db_uri or not db_uri.startswith("db://"):
            raise ValueError("LANCE_DB_URI must be set and start with 'db://'")
        if not api_key:
            raise ValueError("LANCE_API_KEY is missing")

        self.db = lancedb.connect(db_uri, api_key=api_key)
        self.table = self.db.open_table(table_name)
        self.table_name = table_name

    def search(self, query_vector: list[float], top_k: int = 5) -> list[dict]:
        """
        Search for movies matching the query vector.

        Fetches extra results (top_k * 20) to ensure enough unique movies
        after deduplication, since many subtitle chunks from the same
        movie may match.

        Returns a list of { tmdb_id, score } dicts, sorted by score descending.
        """
        # Fetch more results than needed to account for deduplication
        fetch_limit = top_k * 20

        raw_results = (
            self.table.search(query_vector)
            .limit(fetch_limit)
            .to_list()
        )

        # Deduplicate by tmdb_id — keep the best (lowest distance) match per movie
        best_per_movie: dict[int, float] = {}
        for row in raw_results:
            tmdb_id = row["tmdb_id"]
            distance = row.get("_distance", float("inf"))

            if tmdb_id not in best_per_movie or distance < best_per_movie[tmdb_id]:
                best_per_movie[tmdb_id] = distance

        # Convert distance to a 0–1 similarity score (higher = better)
        results = []
        for tmdb_id, distance in best_per_movie.items():
            score = 1.0 / (1.0 + distance)
            results.append({"tmdb_id": tmdb_id, "score": round(score, 4)})

        # Sort by score descending and take top_k
        results.sort(key=lambda r: r["score"], reverse=True)
        return results[:top_k]
