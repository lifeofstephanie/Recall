import { createClient, SupabaseClient } from "@supabase/supabase-js";
import { Request, Response, NextFunction } from "express";
import supabase from "../config/supabase";
import { notifyUser } from "../services/push.service";

import { AuthenticatedRequest } from "../middleware/auth.middleware";

const SUPABASE_URL = process.env.SUPABASE_URL;
const SUPABASE_ANON_KEY = process.env.SUPABASE_ANON_KEY;

if (!SUPABASE_URL || !SUPABASE_ANON_KEY) {
  throw new Error(
    "Missing Supabase environment variables! Check your .env file.",
  );
}

function getAnonClient(): SupabaseClient {
  return createClient(SUPABASE_URL!, SUPABASE_ANON_KEY!);
}

/**
 * POST /api/auth/register
 * Body: { name, email, password }
 */
export async function register(
  req: Request,
  res: Response,
  next: NextFunction,
): Promise<any> {
  try {
    const { name, email, password } = req.body;

    if (!name || !email || !password) {
      return res
        .status(400)
        .json({ error: "Name, email and password are required" });
    }

    const supabaseClient = getAnonClient();

    // Step 1: Create the auth user
    const { data, error } = await supabaseClient.auth.signUp({
      email,
      password,
    });

    if (error) return res.status(400).json({ error: error.message });
    if (!data.user)
      return res.status(400).json({ error: "User signup failed" });

    // Step 2: Create the profile with name (using service role to bypass RLS)
    await supabase.from("profiles").insert({
      id: data.user.id,
      name,
      avatar_url: null,
    });

    return res.status(201).json({
      message:
        "Registration successful. Check your email to confirm your account.",
      user: {
        id: data.user.id,
        email: data.user.email,
        name,
      },
    });
  } catch (err) {
    next(err);
  }
}

/**
 * POST /api/auth/login
 * Body: { email, password }
 */
export async function login(
  req: Request,
  res: Response,
  next: NextFunction,
): Promise<any> {
  try {
    const { email, password } = req.body;

    if (!email || !password) {
      return res.status(400).json({ error: "Email and password are required" });
    }

    const supabaseClient = getAnonClient();
    const { data, error } = await supabaseClient.auth.signInWithPassword({
      email,
      password,
    });

    if (error) return res.status(401).json({ error: error.message });
    if (!data.user || !data.session)
      return res.status(401).json({ error: "Login failed" });

    // Fetch profile (name + avatar)
    const { data: profile } = await supabase
      .from("profiles")
      .select("name, avatar_url")
      .eq("id", data.user.id)
      .single();

    return res.json({
      message: "Login successful",
      user: {
        id: data.user.id,
        email: data.user.email,
        name: profile?.name || null,
        avatar_url: profile?.avatar_url || null,
      },
      session: {
        access_token: data.session.access_token,
        refresh_token: data.session.refresh_token,
        expires_at: data.session.expires_at,
      },
    });
  } catch (err) {
    next(err);
  }
}

/**
 * POST /api/auth/logout
 */
export async function logout(
  req: AuthenticatedRequest,
  res: Response,
  next: NextFunction,
): Promise<any> {
  try {
    const supabaseClient = createClient(SUPABASE_URL!, SUPABASE_ANON_KEY!, {
      global: { headers: { Authorization: `Bearer ${req.token || ""}` } },
    });

    const { error } = await supabaseClient.auth.signOut();
    if (error) return res.status(400).json({ error: error.message });

    return res.json({ message: "Logged out successfully" });
  } catch (err) {
    next(err);
  }
}

/**
 * GET /api/auth/me
 * Returns the authenticated user's full profile.
 */
export async function getMe(
  req: AuthenticatedRequest,
  res: Response,
  next: NextFunction,
): Promise<any> {
  try {
    if (!req.user) return res.status(401).json({ error: "Unauthorized" });

    const { data: profile } = await supabase
      .from("profiles")
      .select("name, avatar_url, updated_at")
      .eq("id", req.user.id)
      .single();

    return res.json({
      user: {
        id: req.user.id,
        email: req.user.email,
        name: profile?.name || null,
        avatar_url: profile?.avatar_url || null,
        created_at: req.user.created_at,
        updated_at: profile?.updated_at || null,
      },
    });
  } catch (err) {
    next(err);
  }
}

/**
 * PATCH /api/auth/profile
 * Body: { name?, password? }
 * Updates the user's name and/or password.
 */
export async function updateProfile(
  req: AuthenticatedRequest,
  res: Response,
  next: NextFunction,
): Promise<any> {
  try {
    if (!req.user) return res.status(401).json({ error: "Unauthorized" });

    const { name, password } = req.body;

    // Update password in Supabase Auth if provided
    if (password) {
      const supabaseClient = createClient(SUPABASE_URL!, SUPABASE_ANON_KEY!, {
        global: { headers: { Authorization: `Bearer ${req.token}` } },
      });
      const { error } = await supabaseClient.auth.updateUser({ password });
      if (error) return res.status(400).json({ error: error.message });

      // Account notification (best-effort).
      notifyUser(req.user.id, {
        title: "Password changed",
        body: "Your Recall password was just changed.",
      }).catch(() => {});
    }

    // Update name in profiles table if provided
    if (name) {
      const { error } = await supabase
        .from("profiles")
        .update({ name, updated_at: new Date().toISOString() })
        .eq("id", req.user.id);

      if (error) return res.status(400).json({ error: error.message });
    }

    return res.json({ message: "Profile updated successfully" });
  } catch (err) {
    next(err);
  }
}

/**
 * POST /api/auth/profile/photo
 * Body: multipart/form-data with field "photo"
 * Uploads a profile photo to Supabase Storage and saves the URL.
 */
export async function uploadProfilePhoto(
  req: AuthenticatedRequest,
  res: Response,
  next: NextFunction,
): Promise<any> {
  try {
    if (!req.user) return res.status(401).json({ error: "Unauthorized" });
    if (!req.file)
      return res.status(400).json({ error: "Photo file is required" });

    const fileExt = req.file.originalname.split(".").pop();
    const filePath = `${req.user.id}/avatar.${fileExt}`;

    // Upload to Supabase Storage (avatars bucket)
    const { error: uploadError } = await supabase.storage
      .from("avatars")
      .upload(filePath, req.file.buffer, {
        contentType: req.file.mimetype,
        upsert: true, // Overwrite existing avatar
      });

    if (uploadError)
      return res.status(400).json({ error: uploadError.message });

    // Get the public URL
    const { data: urlData } = supabase.storage
      .from("avatars")
      .getPublicUrl(filePath);

    const avatar_url = urlData.publicUrl;

    // Save URL to profiles table
    await supabase
      .from("profiles")
      .update({ avatar_url, updated_at: new Date().toISOString() })
      .eq("id", req.user.id);

    return res.json({
      message: "Profile photo updated successfully",
      avatar_url,
    });
  } catch (err) {
    next(err);
  }
}



export async function forgotPassword(
  req: Request,
  res: Response,
  next: NextFunction,
) {
  try {
    const { email } = req.body;

    if (!email) {
      return res.status(400).json({ error: "Email is required" });
    }

    const { error } = await supabase.auth.resetPasswordForEmail(email, {
      redirectTo: process.env.RESET_PASSWORD_URL || "https://your-app.com/reset-password",
    });

    if (error) {
      return res.status(400).json({ error: error.message });
    }

    return res.json({
      message: "Password reset email sent successfully",
    });
  } catch (err) {
    next(err);
  }
}

/**
 * POST /api/auth/refresh
 * Body: { refresh_token }
 * Exchanges a refresh token for a fresh session so users stay logged in
 * across app restarts and past the access-token expiry.
 */
export async function refreshToken(
  req: Request,
  res: Response,
  next: NextFunction,
): Promise<any> {
  try {
    const { refresh_token } = req.body;
    if (!refresh_token) {
      return res.status(400).json({ error: "refresh_token is required" });
    }

    const supabaseClient = getAnonClient();
    const { data, error } = await supabaseClient.auth.refreshSession({
      refresh_token,
    });

    if (error || !data.session || !data.user) {
      return res
        .status(401)
        .json({ error: error?.message || "Could not refresh session" });
    }

    const { data: profile } = await supabase
      .from("profiles")
      .select("name, avatar_url")
      .eq("id", data.user.id)
      .single();

    return res.json({
      user: {
        id: data.user.id,
        email: data.user.email,
        name: profile?.name || null,
        avatar_url: profile?.avatar_url || null,
      },
      session: {
        access_token: data.session.access_token,
        refresh_token: data.session.refresh_token,
        expires_at: data.session.expires_at,
      },
    });
  } catch (err) {
    next(err);
  }
}

/**
 * DELETE /api/auth/account
 * Permanently deletes the signed-in user. Their profile / history / watchlist
 * rows are removed automatically via ON DELETE CASCADE.
 */
export async function deleteAccount(
  req: AuthenticatedRequest,
  res: Response,
  next: NextFunction,
): Promise<any> {
  try {
    if (!req.user) return res.status(401).json({ error: "Unauthorized" });

    const { error } = await supabase.auth.admin.deleteUser(req.user.id);
    if (error) return res.status(400).json({ error: error.message });

    return res.json({ message: "Account deleted" });
  } catch (err) {
    next(err);
  }
}

/**
 * GET /api/auth/preferences
 * Returns the user's stored preferences (with sensible defaults).
 */
export async function getPreferences(
  req: AuthenticatedRequest,
  res: Response,
  next: NextFunction,
): Promise<any> {
  try {
    if (!req.user) return res.status(401).json({ error: "Unauthorized" });

    const { data } = await supabase
      .from("profiles")
      .select("preferences")
      .eq("id", req.user.id)
      .single();

    const prefs = data?.preferences || {};
    return res.json({
      notifications: prefs.notifications ?? true,
      autoplay_trailers: prefs.autoplay_trailers ?? false,
    });
  } catch (err) {
    next(err);
  }
}

/**
 * PATCH /api/auth/preferences
 * Body: { notifications?, autoplay_trailers? } — merged into the stored JSON.
 */
export async function updatePreferences(
  req: AuthenticatedRequest,
  res: Response,
  next: NextFunction,
): Promise<any> {
  try {
    if (!req.user) return res.status(401).json({ error: "Unauthorized" });

    const { notifications, autoplay_trailers } = req.body;

    const { data } = await supabase
      .from("profiles")
      .select("preferences")
      .eq("id", req.user.id)
      .single();

    const updated = { ...(data?.preferences || {}) };
    if (typeof notifications === "boolean") updated.notifications = notifications;
    if (typeof autoplay_trailers === "boolean")
      updated.autoplay_trailers = autoplay_trailers;

    const { error } = await supabase
      .from("profiles")
      .update({ preferences: updated, updated_at: new Date().toISOString() })
      .eq("id", req.user.id);

    if (error) return res.status(400).json({ error: error.message });

    return res.json({
      notifications: updated.notifications ?? true,
      autoplay_trailers: updated.autoplay_trailers ?? false,
    });
  } catch (err) {
    next(err);
  }
}
