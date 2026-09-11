-- ================================================================
-- GIST: Supabase Database Setup
-- Run this in the Supabase SQL Editor (Dashboard > SQL Editor)
-- ================================================================

-- ── profiles ──────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.profiles (
  id          UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  name        TEXT,
  avatar_url  TEXT,
  updated_at  TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can read own profile"
  ON public.profiles FOR SELECT
  USING (auth.uid() = id);

-- ── search_history ────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.search_history (
  id                    UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  user_id               UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  query                 TEXT NOT NULL,
  top_result_tmdb_id    INTEGER,
  top_result_title      TEXT,
  top_result_poster_url TEXT,
  searched_at           TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_search_history_user_id
  ON public.search_history(user_id);
CREATE INDEX IF NOT EXISTS idx_search_history_searched_at
  ON public.search_history(searched_at DESC);

ALTER TABLE public.search_history ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can read own history"
  ON public.search_history FOR SELECT
  USING (auth.uid() = user_id);

CREATE POLICY "Users can delete own history"
  ON public.search_history FOR DELETE
  USING (auth.uid() = user_id);

-- ── watchlist ─────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.watchlist (
  id         UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  user_id    UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  tmdb_id    INTEGER NOT NULL,
  added_at   TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(user_id, tmdb_id)   -- prevent duplicates
);

CREATE INDEX IF NOT EXISTS idx_watchlist_user_id
  ON public.watchlist(user_id);

ALTER TABLE public.watchlist ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can read own watchlist"
  ON public.watchlist FOR SELECT
  USING (auth.uid() = user_id);

CREATE POLICY "Users can delete own watchlist entries"
  ON public.watchlist FOR DELETE
  USING (auth.uid() = user_id);

-- Backend uses service_role key for INSERT (bypasses RLS safely)

-- ── user preferences (notifications, autoplay, etc.) ──────────────
-- Stored as JSON on the profile. Run this if upgrading an existing DB.
ALTER TABLE public.profiles
  ADD COLUMN IF NOT EXISTS preferences JSONB DEFAULT '{}'::jsonb;

-- ── push_tokens (Expo push notification device tokens) ────────────
CREATE TABLE IF NOT EXISTS public.push_tokens (
  id          UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  user_id     UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  token       TEXT NOT NULL UNIQUE,
  platform    TEXT,
  created_at  TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_push_tokens_user_id
  ON public.push_tokens(user_id);
ALTER TABLE public.push_tokens ENABLE ROW LEVEL SECURITY;
-- Backend uses the service_role key (bypasses RLS).

-- ── search_misses (deferred "we found your movie" notifications) ──
-- A row is written when a signed-in user's search returns nothing. After the
-- full library is ingested, an admin re-check finds new matches and notifies.
CREATE TABLE IF NOT EXISTS public.search_misses (
  id          UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  user_id     UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  query       TEXT NOT NULL,
  notified    BOOLEAN DEFAULT FALSE,
  created_at  TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_search_misses_notified
  ON public.search_misses(notified);
ALTER TABLE public.search_misses ENABLE ROW LEVEL SECURITY;