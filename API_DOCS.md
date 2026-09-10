# Gist API — Frontend Integration Guide

The **Gist Gateway** (Node.js/Express, in `backend/gateway`) is the single API the mobile app talks to.
The Python AI service (`backend/ai`) and LanceDB are internal — the frontend never calls them directly.

- **Base URL (local):** `http://localhost:3000`
- **All app routes are prefixed with** `/api`
- **Content type:** `application/json` (except photo upload, which is `multipart/form-data`)
- **Rate limit:** 100 requests / 15 min per IP on `/api/*` (returns `429` with `{ "error": "Too many requests, please try again later." }`)

> **Emulator note:** A phone/emulator cannot reach `localhost`. Use your machine's LAN IP
> (e.g. `http://192.168.x.x:3000`), the Android emulator alias `http://10.0.2.2:3000`,
> or a tunnel (ngrok) during development.

---

## Authentication model

Auth is powered by Supabase. After **login**, you receive an `access_token` (JWT).
Send it on protected routes as a header:

```
Authorization: Bearer <access_token>
```

- **Guest mode:** `POST /api/search` works **with or without** a token. With a token, the search is
  saved to the user's history; without one, it still returns results but saves nothing.
- **Protected routes** (history, watchlist, profile) return `401` if the token is missing/expired.
- Tokens expire (`session.expires_at`). Persist the `refresh_token` from login to refresh the
  session via the Supabase client SDK when the access token expires.

### Standard error shape

Every error responds with an appropriate HTTP status and:

```json
{ "error": "Human-readable message" }
```

| Status | Meaning |
| ------ | ------- |
| 400 | Bad/missing input |
| 401 | Missing, invalid, or expired token |
| 404 | Route or resource not found |
| 409 | Conflict (e.g. movie already in watchlist) |
| 429 | Rate limited |
| 500 | Unexpected server error |
| 503 | AI search service unavailable |

---

## Health

### `GET /health`
No auth. Use for connectivity checks.

**200**
```json
{ "status": "ok", "service": "gist-gateway", "timestamp": "2026-08-31T12:00:00.000Z" }
```

---

## Auth routes — `/api/auth`

### `POST /api/auth/register`
Create an account. Supabase sends a confirmation email; the user must confirm before login
(depending on your Supabase settings).

**Body**
```json
{ "name": "Ada Lovelace", "email": "ada@example.com", "password": "supersecret" }
```
**201**
```json
{
  "message": "Registration successful. Check your email to confirm your account.",
  "user": { "id": "uuid", "email": "ada@example.com", "name": "Ada Lovelace" }
}
```
**400** — missing fields, or email already registered.

---

### `POST /api/auth/login`
**Body**
```json
{ "email": "ada@example.com", "password": "supersecret" }
```
**200**
```json
{
  "message": "Login successful",
  "user": { "id": "uuid", "email": "ada@example.com", "name": "Ada Lovelace", "avatar_url": null },
  "session": {
    "access_token": "eyJhbGciOi...",
    "refresh_token": "v1.M2Rk...",
    "expires_at": 1725110400
  }
}
```
**401** — wrong credentials or unconfirmed account.

> Store `access_token` (for the `Authorization` header) and `refresh_token` (for refreshing) securely
> — use `expo-secure-store` / Keychain / Keystore, not plain AsyncStorage.

---

### `POST /api/auth/logout`  🔒
Header: `Authorization: Bearer <token>`

**200** `{ "message": "Logged out successfully" }`

---

### `GET /api/auth/me`  🔒
**200**
```json
{
  "user": {
    "id": "uuid",
    "email": "ada@example.com",
    "name": "Ada Lovelace",
    "avatar_url": "https://.../avatar.png",
    "created_at": "2026-08-01T10:00:00Z",
    "updated_at": "2026-08-20T09:00:00Z"
  }
}
```

---

### `PATCH /api/auth/profile`  🔒
Update name and/or password. Send either or both.

**Body**
```json
{ "name": "Ada L.", "password": "newpassword" }
```
**200** `{ "message": "Profile updated successfully" }`

---

### `POST /api/auth/profile/photo`  🔒
`multipart/form-data`, single file field named **`photo`**.

**200**
```json
{ "message": "Profile photo updated successfully", "avatar_url": "https://.../avatar.png" }
```
**400** — no file provided.

React Native example:
```js
const form = new FormData();
form.append("photo", { uri, name: "avatar.jpg", type: "image/jpeg" });
await fetch(`${BASE}/api/auth/profile/photo`, {
  method: "POST",
  headers: { Authorization: `Bearer ${token}` }, // do NOT set Content-Type manually
  body: form,
});
```

---

### `POST /api/auth/forgot-password`
No auth. Sends a password-reset email.

**Body** `{ "email": "ada@example.com" }`
**200** `{ "message": "Password reset email sent successfully" }`

---

## Search — `/api/search`

### `POST /api/search`  (auth optional — guest mode)
The core feature. Send the phrase the user typed **or** the text produced by on-device
speech-to-text. The gateway asks the AI service for the best-matching movies, enriches them with
TMDb data, and (if a token is sent) saves the search to history.

**Body**
```json
{ "query": "purple guy snapping his fingers", "top_k": 5 }
```
| Field | Type | Required | Notes |
| ----- | ---- | -------- | ----- |
| `query` | string | ✅ | The remembered line/phrase (1–500 chars). |
| `top_k` | number | ❌ | How many results (default 5, max 20). |

**200** — results sorted by `confidence_score` (highest first):
```json
{
  "query": "purple guy snapping his fingers",
  "result_count": 5,
  "results": [
    {
      "tmdb_id": 299536,
      "title": "Avengers: Infinity War",
      "overview": "As the Avengers and their allies have continued...",
      "release_date": "2018-04-25",
      "release_year": "2018",
      "genres": ["Adventure", "Action", "Science Fiction"],
      "rating": 8.2,
      "vote_count": 28000,
      "runtime": 149,
      "poster_url": "https://image.tmdb.org/t/p/w500/....jpg",
      "backdrop_url": "https://image.tmdb.org/t/p/w1280/....jpg",
      "cast": [
        { "name": "Robert Downey Jr.", "character": "Tony Stark / Iron Man", "profile_url": "https://image.tmdb.org/t/p/w500/....jpg" }
      ],
      "trailer_url": "https://www.youtube.com/watch?v=xxxx",
      "confidence_score": 0.9821
    }
  ]
}
```
**200 (no matches)** — note the shape differs slightly (no `result_count`):
```json
{ "query": "asdfghjkl", "results": [] }
```
**400** `{ "error": "A search query is required" }` — empty/whitespace query.
**503** `{ "error": "AI search service is unavailable. Please try again shortly." }` — AI service down.

> **Field notes:** any of `poster_url`, `backdrop_url`, `trailer_url`, or a cast member's
> `profile_url` may be `null`. `confidence_score` is a 0–1 relevance score. Handle missing posters
> with a placeholder image.

---

## Search History — `/api/history`  🔒
All routes require a token.

### `GET /api/history?limit=20&offset=0`
Paginated, newest first. `limit` defaults to 20 (max 100), `offset` defaults to 0.

**200**
```json
{
  "total": 42,
  "limit": 20,
  "offset": 0,
  "entries": [
    {
      "id": "uuid",
      "user_id": "uuid",
      "query": "purple guy snapping his fingers",
      "top_result_tmdb_id": 299536,
      "top_result_title": "Avengers: Infinity War",
      "top_result_poster_url": "https://image.tmdb.org/t/p/w500/....jpg",
      "searched_at": "2026-08-31T12:00:00Z"
    }
  ]
}
```

### `DELETE /api/history/:id`
Delete one entry (only the caller's own). **200** `{ "message": "History entry deleted" }`

### `DELETE /api/history`
Clear all of the caller's history. **200** `{ "message": "Search history cleared" }`

---

## Watchlist — `/api/watchlist`  🔒
All routes require a token.

### `GET /api/watchlist`
Returns saved movies, each re-enriched with fresh TMDb data plus an `added_at` timestamp.

**200 (has items)**
```json
{
  "count": 2,
  "movies": [
    {
      "tmdb_id": 299536,
      "title": "Avengers: Infinity War",
      "overview": "...",
      "release_date": "2018-04-25",
      "release_year": "2018",
      "genres": ["Action"],
      "rating": 8.2,
      "vote_count": 28000,
      "runtime": 149,
      "poster_url": "https://image.tmdb.org/t/p/w500/....jpg",
      "backdrop_url": "https://image.tmdb.org/t/p/w1280/....jpg",
      "cast": [{ "name": "...", "character": "...", "profile_url": null }],
      "trailer_url": "https://www.youtube.com/watch?v=xxxx",
      "added_at": "2026-08-30T18:00:00Z"
    }
  ]
}
```
**200 (empty)** — note: no `count` field when empty:
```json
{ "movies": [] }
```

### `POST /api/watchlist`
**Body** `{ "tmdb_id": 299536 }`
**201** `{ "message": "Movie added to watchlist" }`
**400** `{ "error": "A valid tmdb_id is required" }`
**409** `{ "error": "Movie is already in your watchlist" }`

### `DELETE /api/watchlist/:tmdbId`
**200** `{ "message": "Movie removed from watchlist" }`
**400** `{ "error": "Invalid tmdb_id" }`

### `GET /api/watchlist/:tmdbId/check`
Quick check for toggling a "saved" icon. Always **200**:
```json
{ "in_watchlist": true }
```

---

## Typical flows

**Guest search → detail:**
`POST /api/search` (no token) → render `results` → tap a card → you already have full detail in the
result object (cast, trailer, genres, poster), so no extra call is needed.

**Signed-in search:**
`POST /api/login` → store tokens → `POST /api/search` (with token) → search auto-saved →
`GET /api/history` shows it later.

**Watchlist toggle on a result card:**
`GET /api/watchlist/:tmdbId/check` to set initial icon → `POST /api/watchlist` to add /
`DELETE /api/watchlist/:tmdbId` to remove.

---

## Quick reference

| Method | Path | Auth | Purpose |
| ------ | ---- | ---- | ------- |
| GET | `/health` | – | Connectivity check |
| POST | `/api/auth/register` | – | Create account |
| POST | `/api/auth/login` | – | Log in, get tokens |
| POST | `/api/auth/logout` | 🔒 | Log out |
| GET | `/api/auth/me` | 🔒 | Current user profile |
| PATCH | `/api/auth/profile` | 🔒 | Update name/password |
| POST | `/api/auth/profile/photo` | 🔒 | Upload avatar (multipart) |
| POST | `/api/auth/forgot-password` | – | Send reset email |
| POST | `/api/search` | Optional | Semantic movie search |
| GET | `/api/history` | 🔒 | List search history |
| DELETE | `/api/history/:id` | 🔒 | Delete one history entry |
| DELETE | `/api/history` | 🔒 | Clear all history |
| GET | `/api/watchlist` | 🔒 | List saved movies |
| POST | `/api/watchlist` | 🔒 | Add to watchlist |
| DELETE | `/api/watchlist/:tmdbId` | 🔒 | Remove from watchlist |
| GET | `/api/watchlist/:tmdbId/check` | 🔒 | Is movie saved? |

🔒 = requires `Authorization: Bearer <access_token>`
