import { createClient } from "@supabase/supabase-js";
import { NextFunction, Request, Response } from "express";

// 1. Extend the Express Request interface globally or for these middleware functions
export interface AuthenticatedRequest extends Request {
  user?: any | null; // Set to any to match Supabase's internal User object, or import { User } from '@supabase/supabase-js'
  token?: string;
}

// 2. Safely extract environment variables with fallbacks to pass strict checks
const SUPABASE_URL = process.env.SUPABASE_URL || "";
const SUPABASE_ANON_KEY = process.env.SUPABASE_ANON_KEY || "";

if (!SUPABASE_URL || !SUPABASE_ANON_KEY) {
  throw new Error(
    "Missing Supabase configuration. Check your environment variables.",
  );
}

/**
 * Middleware: verifyToken
 * Attaches the user and token to the request object if a valid Bearer token is provided.
 */
export async function verifyToken(
  req: AuthenticatedRequest,
  res: Response,
  next: NextFunction,
): Promise<any> {
  const authHeader = req.headers.authorization;

  // Guest mode — no token required for search, but history requires auth
  if (!authHeader || !authHeader.startsWith("Bearer ")) {
    req.user = null;
    return next();
  }

  const token = authHeader.split(" ")[1];

  try {
    // Create a per-request client with the user's token to validate it
    const supabase = createClient(SUPABASE_URL, SUPABASE_ANON_KEY);

    const {
      data: { user },
      error,
    } = await supabase.auth.getUser(token);

    if (error || !user) {
      return res.status(401).json({ error: "Invalid or expired token" });
    }

    req.user = user;
    req.token = token;
    return next();
  } catch (err) {
    return res.status(401).json({ error: "Token validation failed" });
  }
}

/**
 * Middleware: requireAuth
 * Use on routes that must have an authenticated user (e.g. search history).
 * Always stack AFTER verifyToken.
 */
export function requireAuth(
  req: AuthenticatedRequest,
  res: Response,
  next: NextFunction,
): any {
  if (!req.user) {
    return res.status(401).json({ error: "Authentication required" });
  }
  return next();
}
