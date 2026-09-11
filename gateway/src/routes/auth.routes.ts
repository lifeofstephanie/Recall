import express from "express";
import multer from "multer";
import {
  register,
  login,
  logout,
  getMe,
  updateProfile,
  uploadProfilePhoto,
  forgotPassword,
  refreshToken,
  deleteAccount,
  getPreferences,
  updatePreferences,
} from "../controllers/auth.controller";
import { verifyToken, requireAuth } from "../middleware/auth.middleware";

const router = express.Router();
const upload = multer({ storage: multer.memoryStorage() });

// POST /api/auth/register  — name, email, password
router.post("/register", register);

// POST /api/auth/login
router.post("/login", login);

// POST /api/auth/logout
router.post("/logout", verifyToken, requireAuth, logout);

// GET /api/auth/me
router.get("/me", verifyToken, requireAuth, getMe);

// PATCH /api/auth/profile  — update name and/or password
router.patch("/profile", verifyToken, requireAuth, updateProfile);

// POST /api/auth/profile/photo  — upload profile picture
router.post(
  "/profile/photo",
  verifyToken,
  requireAuth,
  upload.single("photo"),
  uploadProfilePhoto,
);
router.post("/forgot-password", forgotPassword);
router.post("/refresh", refreshToken);

// Account management
router.delete("/account", verifyToken, requireAuth, deleteAccount);
router.get("/preferences", verifyToken, requireAuth, getPreferences);
router.patch("/preferences", verifyToken, requireAuth, updatePreferences);

export default router;
