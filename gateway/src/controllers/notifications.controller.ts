import { NextFunction, Request, Response } from "express";
import supabase from "../config/supabase";
import { AuthenticatedRequest } from "../middleware/auth.middleware";
import { searchMovies } from "../services/ai.service";
import { notifyUser, sendPush } from "../services/push.service";
import { enrichMovies } from "../services/tmdb.service";

/** Admin routes are gated by a shared secret header (no admin role exists). */
function isAdmin(req: Request): boolean {
  const secret = process.env.ADMIN_SECRET;
  return !!secret && req.headers["x-admin-secret"] === secret;
}

/**
 * POST /api/notifications/register-token   (auth)
 * Body: { token, platform } — saves the caller's Expo push token.
 */
export async function registerToken(
  req: AuthenticatedRequest,
  res: Response,
  next: NextFunction,
): Promise<any> {
  try {
    if (!req.user) return res.status(401).json({ error: "Unauthorized" });
    const { token, platform } = req.body;
    if (!token) return res.status(400).json({ error: "token is required" });

    await supabase
      .from("push_tokens")
      .upsert(
        { user_id: req.user.id, token, platform: platform || null },
        { onConflict: "token" },
      );

    return res.json({ message: "Token registered" });
  } catch (err) {
    next(err);
  }
}

/**
 * POST /api/notifications/broadcast   (admin secret)
 * Body: { title, body, data? } — sends to every registered device.
 * Use for maintenance notices, announcements, etc.
 */
export async function broadcast(
  req: Request,
  res: Response,
  next: NextFunction,
): Promise<any> {
  try {
    if (!isAdmin(req)) return res.status(403).json({ error: "Forbidden" });
    const { title, body, data } = req.body;
    if (!title || !body) {
      return res.status(400).json({ error: "title and body are required" });
    }

    const { data: rows } = await supabase.from("push_tokens").select("token");
    await sendPush(
      (rows ?? []).map((r: { token: string }) => r.token),
      { title, body, data },
    );

    return res.json({ message: "Broadcast sent", recipients: rows?.length ?? 0 });
  } catch (err) {
    next(err);
  }
}

/**
 * POST /api/notifications/recheck-misses   (admin secret)
 * Re-runs each un-notified "search miss" against the AI service; when a match
 * now exists (e.g. after a bigger ingest), notifies the user. Run after ingest.
 */
export async function recheckMisses(
  req: Request,
  res: Response,
  next: NextFunction,
): Promise<any> {
  try {
    if (!isAdmin(req)) return res.status(403).json({ error: "Forbidden" });

    const { data: misses } = await supabase
      .from("search_misses")
      .select("*")
      .eq("notified", false)
      .limit(200);

    let notified = 0;
    for (const miss of misses ?? []) {
      try {
        const results = await searchMovies(miss.query, 1);
        if (results && results.length > 0) {
          const [movie] = await enrichMovies([results[0].tmdb_id]);
          await notifyUser(miss.user_id, {
            title: "We found your movie! 🎬",
            body: movie
              ? `"${miss.query}" → ${movie.title}`
              : `We found a match for "${miss.query}"`,
            data: { tmdb_id: results[0].tmdb_id },
          });
          await supabase
            .from("search_misses")
            .update({ notified: true })
            .eq("id", miss.id);
          notified++;
        }
      } catch {
        // skip this miss; try the rest
      }
    }

    return res.json({ checked: misses?.length ?? 0, notified });
  } catch (err) {
    next(err);
  }
}
