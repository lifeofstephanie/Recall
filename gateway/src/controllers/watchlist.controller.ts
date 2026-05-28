import { Request, Response, NextFunction } from "express";
import supabase from "../config/supabase";
import { getMovieDetails } from "../services/tmdb.service";

// ── Types ───────────────────────────────────────────────────────────────────

interface AuthenticatedRequest extends Request {
  user?: {
    id: string;
    email: string;
    created_at: string;
  };
}

interface WatchlistEntry {
  tmdb_id: number;
  added_at: string;
}

interface MovieDetails {
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
  cast: {
    name: string;
    character: string;
    profile_url: string | null;
  }[];
  trailer_url: string | null;
}

// ── Controllers ─────────────────────────────────────────────────────────────

/**
 * GET /api/watchlist
 * Fetches all watchlisted TMDb IDs for the user, then enriches each
 * with fresh TMDb metadata in parallel.
 */
export async function getWatchlist(
  req: AuthenticatedRequest,
  res: Response,
  next: NextFunction,
): Promise<void> {
  try {
    const { data, error } = await supabase
      .from("watchlist")
      .select("tmdb_id, added_at")
      .eq("user_id", req.user!.id)
      .order("added_at", { ascending: false });

    if (error) throw error;
    if (!data || data.length === 0) {
      res.json({ movies: [] });
      return;
    }

    const entries = data as WatchlistEntry[];

    // Fetch fresh TMDb details for all watchlisted movies in parallel
    const movieResults = await Promise.allSettled(
      entries.map((entry) => getMovieDetails(entry.tmdb_id)),
    );

    const movies = movieResults
      .map((result, i) => {
        if (result.status === "fulfilled") {
          return { ...result.value, added_at: entries[i].added_at };
        }
        return null;
      })
      .filter(
        (movie): movie is MovieDetails & { added_at: string } => movie !== null,
      );

    res.json({ count: movies.length, movies });
  } catch (err) {
    next(err);
  }
}

/**
 * POST /api/watchlist
 * Body: { tmdb_id: number }
 */
export async function addToWatchlist(
  req: AuthenticatedRequest,
  res: Response,
  next: NextFunction,
): Promise<void> {
  try {
    const { tmdb_id } = req.body as { tmdb_id: number };

    if (!tmdb_id || isNaN(Number(tmdb_id))) {
      res.status(400).json({ error: "A valid tmdb_id is required" });
      return;
    }

    const { data: existing } = await supabase
      .from("watchlist")
      .select("id")
      .eq("user_id", req.user!.id)
      .eq("tmdb_id", tmdb_id)
      .single();

    if (existing) {
      res.status(409).json({ error: "Movie is already in your watchlist" });
      return;
    }

    const { error } = await supabase.from("watchlist").insert({
      user_id: req.user!.id,
      tmdb_id: Number(tmdb_id),
      added_at: new Date().toISOString(),
    });

    if (error) throw error;

    res.status(201).json({ message: "Movie added to watchlist" });
  } catch (err) {
    next(err);
  }
}

/**
 * DELETE /api/watchlist/:tmdbId
 */
export async function removeFromWatchlist(
  req: AuthenticatedRequest,
  res: Response,
  next: NextFunction,
): Promise<void> {
  try {
    const tmdbId = Number(req.params.tmdbId);

    if (isNaN(tmdbId)) {
      res.status(400).json({ error: "Invalid tmdb_id" });
      return;
    }

    const { error } = await supabase
      .from("watchlist")
      .delete()
      .eq("user_id", req.user!.id)
      .eq("tmdb_id", tmdbId);

    if (error) throw error;

    res.json({ message: "Movie removed from watchlist" });
  } catch (err) {
    next(err);
  }
}

/**
 * GET /api/watchlist/:tmdbId/check
 */
export async function checkWatchlist(
  req: AuthenticatedRequest,
  res: Response,
  next: NextFunction,
): Promise<void> {
  try {
    const tmdbId = Number(req.params.tmdbId);

    const { data } = await supabase
      .from("watchlist")
      .select("id")
      .eq("user_id", req.user!.id)
      .eq("tmdb_id", tmdbId)
      .single();

    res.json({ in_watchlist: !!data });
  } catch {
    res.json({ in_watchlist: false });
  }
}
