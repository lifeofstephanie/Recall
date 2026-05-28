import axios from "axios";

const TMDB_BASE_URL: string =
  process.env.TMDB_BASE_URL || "https://api.themoviedb.org/3";
const TMDB_API_KEY: string | undefined = process.env.TMDB_API_KEY;
const TMDB_IMAGE_BASE: string = "https://image.tmdb.org/t/p/w500";

// Define strict interfaces for your data structures
export interface CastMember {
  name: string;
  character: string;
  profile_url: string | null;
}

export interface EnrichedMovie {
  tmdb_id: number;
  title: string;
  overview: string;
  release_date: string;
  release_year: string | null;
  genres: string[];
  rating: number;
  vote_count: number;
  runtime: number;
  poster_url: string | null;
  backdrop_url: string | null;
  cast: CastMember[];
  trailer_url: string | null;
}

/**
 * Fetch full movie details for a single TMDb movie ID.
 * Includes: overview, cast (top 10), genres, rating, trailer link.
 */
export async function getMovieDetails(
  tmdbId: number | string,
): Promise<EnrichedMovie> {
  const [details, credits, videos] = await Promise.all([
    tmdbGet(`/movie/${tmdbId}`),
    tmdbGet(`/movie/${tmdbId}/credits`),
    tmdbGet(`/movie/${tmdbId}/videos`),
  ]);

  const trailer = videos.results?.find(
    (v: any) => v.type === "Trailer" && v.site === "YouTube",
  );

  return {
    tmdb_id: details.id,
    title: details.title,
    overview: details.overview,
    release_date: details.release_date,
    release_year: details.release_date?.split("-")[0] || null,
    genres: details.genres?.map((g: any) => g.name) || [],
    rating: details.vote_average,
    vote_count: details.vote_count,
    runtime: details.runtime,
    poster_url: details.poster_path
      ? `${TMDB_IMAGE_BASE}${details.poster_path}`
      : null,
    backdrop_url: details.backdrop_path
      ? `https://image.tmdb.org/t/p/w1280${details.backdrop_path}`
      : null,
    cast:
      credits.cast?.slice(0, 10).map((c: any) => ({
        name: c.name,
        character: c.character,
        profile_url: c.profile_path
          ? `${TMDB_IMAGE_BASE}${c.profile_path}`
          : null,
      })) || [],
    trailer_url: trailer
      ? `https://www.youtube.com/watch?v=${trailer.key}`
      : null,
  };
}

/**
 * Fetch enriched metadata for a list of TMDb IDs in parallel.
 * Used after the AI microservice returns the top 5 matches.
 */
export async function enrichMovies(
  tmdbIds: (number | string)[],
): Promise<EnrichedMovie[]> {
  const results = await Promise.allSettled(
    tmdbIds.map((id) => getMovieDetails(id)),
  );

  return results
    .filter(
      (r): r is PromiseFulfilledResult<EnrichedMovie> =>
        r.status === "fulfilled",
    )
    .map((r) => r.value);
}

/**
 * Internal helper: GET request to TMDb with API key.
 */
async function tmdbGet(
  path: string,
  params: Record<string, any> = {},
): Promise<any> {
  const response = await axios.get(`${TMDB_BASE_URL}${path}`, {
    params: { api_key: TMDB_API_KEY, ...params },
    timeout: 8000,
  });
  return response.data;
}
