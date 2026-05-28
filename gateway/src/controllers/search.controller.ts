import { NextFunction, Request, Response } from "express";
import { searchMovies } from "../services/ai.service";
import { enrichMovies } from "../services/tmdb.service";
import supabase from "../config/supabase";

// 1. Interfaces for the incoming AI data structure
interface MovieAiResult {
  tmdb_id: number;
  score: number;
}

// 2. Extend the standard Express request object to recognize req.user
interface AuthenticatedRequest extends Request {
  user?: {
    id: string;
    email: string;
    created_at: string;
  };
}

/**
 * POST /api/search
 *
 * Full search flow:
 * 1. Receive query from client (typed or voice-transcribed text)
 * 2. Forward to Python AI microservice → get top TMDb IDs + scores
 * 3. Enrich each result with full TMDb metadata
 * 4. If user is authenticated, save query to search history
 * 5. Return enriched results to client
 */
export async function search(
  req: AuthenticatedRequest,
  res: Response,
  next: NextFunction,
): Promise<any> {
  try {
    const { query, top_k = 5 } = req.body;

    if (!query || typeof query !== "string" || query.trim().length === 0) {
      return res.status(400).json({ error: "A search query is required" });
    }

    const trimmedQuery: string = query.trim();

    // ── Step 1: Get AI results ──────────────────────────────────────────
    let aiResults: MovieAiResult[];
    try {
      aiResults = await searchMovies(trimmedQuery, top_k);
    } catch (aiError: any) {
      console.error("[Search] FULL AI ERROR:", {
        message: aiError.message,
        code: aiError.code,
        response: aiError.response?.data,
        status: aiError.response?.status,
      });
      return res.status(503).json({
        error: "AI search service is unavailable. Please try again shortly.",
      });
    }

    if (!aiResults || aiResults.length === 0) {
      return res.json({ query: trimmedQuery, results: [] });
    }

    // ── Step 2: Enrich with TMDb metadata ───────────────────────────────
    const tmdbIds: number[] = aiResults.map((r) => r.tmdb_id);
    const movieDetails = await enrichMovies(tmdbIds);

    // Merge AI confidence scores into TMDb results
    const enriched = movieDetails.map((movie) => {
      const aiMatch = aiResults.find((r) => r.tmdb_id === movie.tmdb_id);
      return {
        ...movie,
        confidence_score: aiMatch ? parseFloat(aiMatch.score.toFixed(4)) : null,
      };
    });

    // Sort by confidence score descending
    enriched.sort(
      (a, b) => (b.confidence_score || 0) - (a.confidence_score || 0),
    );

    // ── Step 3: Save to search history (authenticated users only) ────────
    if (req.user) {
      saveSearchHistory(req.user.id, trimmedQuery, enriched[0] || null).catch(
        (err: any) =>
          console.error("[Search] Failed to save history:", err.message),
      );
    }

    return res.json({
      query: trimmedQuery,
      result_count: enriched.length,
      results: enriched,
    });
  } catch (err) {
    next(err);
  }
}

/**
 * Fire-and-forget: save the search query + top result to Supabase.
 * Runs async so it never blocks the search response.
 */
async function saveSearchHistory(
  userId: string,
  query: string,
  topResult: any,
): Promise<void> {
  await supabase.from("search_history").insert({
    user_id: userId,
    query,
    top_result_tmdb_id: topResult?.tmdb_id || null,
    top_result_title: topResult?.title || null,
    top_result_poster_url: topResult?.poster_url || null,
    searched_at: new Date().toISOString(),
  });
}
