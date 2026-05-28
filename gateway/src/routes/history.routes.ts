import express from "express";
import {
  getHistory,
  deleteEntry,
  clearHistory,
} from "../controllers/history.controller";

import { verifyToken, requireAuth } from "../middleware/auth.middleware";

const router = express.Router();

// All history routes require authentication
router.use(verifyToken, requireAuth);

router.get("/", getHistory);

router.delete("/:id", deleteEntry);

router.delete("/", clearHistory);

export default router;
