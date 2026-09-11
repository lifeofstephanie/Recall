import express from "express";
import { getMovie } from "../controllers/movie.controller";

const router = express.Router();

// GET /api/movie/:id  — full TMDb details for one movie (public)
router.get("/:id", getMovie);

export default router;
