import express from "express";
import {
  broadcast,
  recheckMisses,
  registerToken,
} from "../controllers/notifications.controller";
import { requireAuth, verifyToken } from "../middleware/auth.middleware";

const router = express.Router();

// Client registers its Expo push token (auth required)
router.post("/register-token", verifyToken, requireAuth, registerToken);

// Admin-only (guarded by x-admin-secret header inside the controller)
router.post("/broadcast", broadcast);
router.post("/recheck-misses", recheckMisses);

export default router;
