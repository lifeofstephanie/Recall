import axios, { AxiosResponse } from "axios";

const AI_SERVICE_URL: string =
  process.env.AI_SERVICE_URL || "http://localhost:8000";

// Define the structural contract for the movie scores returned by your Python backend
export interface MovieAiResult {
  tmdb_id: number;
  score: number;
}

interface ApiResponse {
  results: MovieAiResult[];
}

/**
 * Send a text query to the Python AI microservice.
 * Returns an array of { tmdb_id, score } objects ranked by confidence.
 */
export async function searchMovies(
  query: string,
  topK: number = 5,
): Promise<MovieAiResult[]> {
  const response: AxiosResponse<ApiResponse> = await axios.post(
    `${AI_SERVICE_URL}/search`,
    { query, top_k: topK },
    { timeout: 60000 }, // AI inference can take a moment on free tiers
  );

  return response.data.results; // [{ tmdb_id, score }, ...]
}


