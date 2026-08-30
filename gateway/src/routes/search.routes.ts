import express from "express";
const router = express.Router();
import * as searchController from "../controllers/search.controller";
import { verifyToken } from "../middleware/auth.middleware";

// POST /api/search
// Body: { query: string, top_k?: number }
// Auth: optional (guest mode supported — history not saved for guests)
router.post("/", verifyToken, searchController.search);

export default router;
