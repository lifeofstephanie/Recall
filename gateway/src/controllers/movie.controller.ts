import { NextFunction, Request, Response } from "express";
import { getMovieDetails } from "../services/tmdb.service";

/**
 * GET /api/movie/:id
 * Fetch full TMDb metadata for a single movie id. Public (no auth) — used by
 * the app to open full details from history/watchlist/search-result cards that
 * only carry a tmdb_id.
 */
export async function getMovie(
  req: Request,
  res: Response,
  next: NextFunction,
): Promise<any> {
  try {
    const id = Number(req.params.id);
    if (Number.isNaN(id)) {
      return res.status(400).json({ error: "Invalid movie id" });
    }
    const movie = await getMovieDetails(id);
    return res.json(movie);
  } catch (err) {
    next(err);
  }
}
