# Gist Gateway Microservice

A Node.js/Express API that acts as the entry point for the Gist mobile app. It handles authentication, forwards search requests to the AI service, enriches results with TMDb data, and manages user watchlists and search history.

## Stack
- Node.js + Express
- TypeScript
- Supabase (Auth & Database)
- TMDb API (Movie Metadata)

## Quick Start

```bash
# 1. Install dependencies
npm install

# 2. Configure environment variables
cp .env.example .env
# Fill in SUPABASE_URL, SUPABASE_ANON_KEY, TMDB_API_KEY, AI_SERVICE_URL, RESET_PASSWORD_URL

# 3. Start development server
npm run dev
```

## API Endpoints

### Authentication
- `POST /api/auth/register` — Create account (name, email, password)
- `POST /api/auth/login` — Login (email, password)
- `POST /api/auth/logout` — Logout user (Requires Bearer token)
- `GET /api/auth/me` — Get profile info
- `PATCH /api/auth/profile` — Update name or password
- `POST /api/auth/profile/photo` — Upload avatar image
- `POST /api/auth/forgot-password` — Request password reset email

### Search
- `POST /api/search` — Semantic movie search (query, top_k)
  - Supports Guest mode (no token needed)
  - Enriches AI results with TMDb posters, cast, runtime, genres, trailers.
  - Automatically saves to history if token is provided.

### History
- `GET /api/history` — Get user's search history (paginated)
- `DELETE /api/history/:id` — Delete a specific history entry
- `DELETE /api/history` — Clear all history

### Watchlist
- `GET /api/watchlist` — Get user's saved movies
- `POST /api/watchlist` — Add movie to watchlist (body: `{ tmdb_id }`)
- `DELETE /api/watchlist/:tmdbId` — Remove movie from watchlist
- `GET /api/watchlist/:tmdbId/check` — Check if a movie is in watchlist

## Environment Variables
- `PORT` - Server port (default 3000)
- `NODE_ENV` - `development` or `production`
- `SUPABASE_URL` - Supabase project URL
- `SUPABASE_ANON_KEY` - Supabase anon/public key
- `TMDB_API_KEY` - The Movie Database API key
- `AI_SERVICE_URL` - URL of the Python AI service (e.g. `http://localhost:7860`)
- `RATE_LIMIT_WINDOW_MS` - Rate limiting window
- `RATE_LIMIT_MAX_REQUESTS` - Rate limiting max requests per window
- `RESET_PASSWORD_URL` - Client URL to handle password reset
