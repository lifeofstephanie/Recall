import { NextFunction, Request, Response } from "express";
import supabase from "../config/supabase";

interface AuthenticatedRequest extends Request {
  user?: {
    id: string;
    email: string;
    created_at: string;
  };
}

export async function getHistory(
  req: AuthenticatedRequest,
  res: Response,
  next: NextFunction,
): Promise<any> {
  try {
    const limitQuery =
      typeof req.query.limit === "string" ? req.query.limit : "20";
    const offsetQuery =
      typeof req.query.offset === "string" ? req.query.offset : "0";

    const limit: number = Math.min(parseInt(limitQuery, 10) || 20, 100);
    const offset: number = parseInt(offsetQuery, 10) || 0;

    if (!req.user?.id) {
      return res.status(401).json({ error: "Unauthorized access" });
    }

    const { data, error, count } = await supabase
      .from("search_history")
      .select("*", { count: "exact" })
      .eq("user_id", req.user.id)
      .order("searched_at", { ascending: false })
      .range(offset, offset + limit - 1);

    if (error) throw error;

    return res.json({
      total: count,
      limit,
      offset,
      entries: data,
    });
  } catch (err) {
    next(err);
  }
}

/**
 * DELETE /api/history/:id
 * Deletes a single history entry (only if it belongs to the user).
 */
export async function deleteEntry(
  req: AuthenticatedRequest,
  res: Response,
  next: NextFunction,
): Promise<any> {
  try {
    const { id } = req.params;

    if (!req.user?.id) {
      return res.status(401).json({ error: "Unauthorized access" });
    }

    const { error } = await supabase
      .from("search_history")
      .delete()
      .eq("id", id)
      .eq("user_id", req.user.id); // Ensure ownership

    if (error) throw error;

    return res.json({ message: "History entry deleted" });
  } catch (err) {
    next(err);
  }
}

/**
 * DELETE /api/history
 * Clears all history entries for the authenticated user.
 */
export async function clearHistory(
  req: AuthenticatedRequest,
  res: Response,
  next: NextFunction,
): Promise<any> {
  try {
    if (!req.user?.id) {
      return res.status(401).json({ error: "Unauthorized access" });
    }

    const { error } = await supabase
      .from("search_history")
      .delete()
      .eq("user_id", req.user.id);

    if (error) throw error;

    return res.json({ message: "Search history cleared" });
  } catch (err) {
    next(err);
  }
}
