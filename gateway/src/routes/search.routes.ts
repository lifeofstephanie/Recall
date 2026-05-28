const express = require("express");
const router = express.Router();
const searchController = require("../controllers/search.controller");
const { verifyToken } = require("../middleware/auth.middleware");

// POST /api/search
// Body: { query: string, top_k?: number }
// Auth: optional (guest mode supported — history not saved for guests)
router.post("/", verifyToken, searchController.search);

export default router;
