import { Router } from "express";
import {
  getWatchlist,
  addToWatchlist,
  removeFromWatchlist,
  checkWatchlist,
} from "../controllers/watchlist.controller";
import { verifyToken, requireAuth } from "../middleware/auth.middleware";

const router = Router();

// All watchlist routes require authentication
router.use(verifyToken, requireAuth);

// GET    /api/watchlist              — get all watchlisted movies (with fresh TMDb data)
router.get("/", getWatchlist);

// POST   /api/watchlist              — add a movie to watchlist
router.post("/", addToWatchlist);

// DELETE /api/watchlist/:tmdbId      — remove a movie from watchlist
router.delete("/:tmdbId", removeFromWatchlist);

// GET    /api/watchlist/:tmdbId/check — check if a movie is in watchlist
router.get("/:tmdbId/check", checkWatchlist);

export default router;
