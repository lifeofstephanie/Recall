# Deploying the Gist Backend

Both compute services run on **Render's free tier**. The data stores (**LanceDB Cloud**,
**Supabase**) are already live, so nothing to host there.

| Service | Folder | Host | Notes |
| ------- | ------ | ---- | ----- |
| AI microservice | `ai/` | Render web service (Python) | ONNX embeddings (`fastembed`, no PyTorch) — ~260 MB RAM, fits the 512 MB free tier |
| Gateway API | `gateway/` | Render web service (Node) | Lightweight; the frontend talks only to this |

Both are defined in **`render.yaml`**, so a single Render Blueprint creates them together.

**Data flow once live:** `Frontend → gist-gateway → gist-ai → LanceDB` and `gist-gateway → TMDb / Supabase`.

---

## 0. Prerequisites

- Accounts: [GitHub](https://github.com), [Render](https://render.com). **No Hugging Face, no card.**
- Backend repo: **`github.com/lifeofstephanie/Recall`** (separate from the frontend repo
  `Parachurami/Recall`).
- Run git commands from the **`backend/`** folder.

### Push the deploy changes first (Render deploys from GitHub)

```bash
cd backend
git add -A
git commit -m "Slim AI service to ONNX; deploy both services on Render"
git push origin main
```

---

## 1. Create both services from the Blueprint

1. render.com → **New → Blueprint**.
2. Connect the **`lifeofstephanie/Recall`** repo. Render reads `render.yaml` and proposes two web
   services: **`gist-ai`** (Python) and **`gist-gateway`** (Node).
3. Click **Apply** — Render will prompt for the `sync: false` env vars (below).

### `gist-ai` secrets
| Key | Value |
| --- | ----- |
| `LANCE_DB_URI` | your `db://…` URI |
| `LANCE_API_KEY` | your LanceDB Cloud key |

(`LANCE_TABLE_NAME` is preset to `movie_quotes` in `render.yaml` — change it there if your table
differs. `PYTHON_VERSION` is pinned to 3.11.)

### `gist-gateway` secrets
| Key | Value |
| --- | ----- |
| `SUPABASE_URL` | your Supabase project URL |
| `SUPABASE_ANON_KEY` | Supabase anon/public key |
| `SUPABASE_SERVICE_ROLE_KEY` | Supabase service-role key |
| `TMDB_API_KEY` | your TMDb key |
| `AI_SERVICE_URL` | the **`gist-ai`** public URL, e.g. `https://gist-ai.onrender.com` (no trailing slash) |
| `RESET_PASSWORD_URL` | your app's reset-password URL |

> **Order tip:** `gist-ai` gets its URL as soon as it's created. Grab it from the `gist-ai` service
> page and paste it into `gist-gateway`'s `AI_SERVICE_URL`, then let the gateway deploy.

---

## 2. Build notes (already handled by `render.yaml`)

- **gist-ai** — build: `pip install -r requirements.txt` + a one-line model pre-download so the ONNX
  MiniLM model is baked in at build time (no cold-start download). Start:
  `uvicorn main:app --host 0.0.0.0 --port $PORT` (Render injects `$PORT`). Health: `/health`.
- **gist-gateway** — build: `npm install && npm run build`. Start: `npm start` (`node dist/index.js`).
  Health: `/health`.

---

## 3. Smoke test

```bash
# AI service (internal contract)
curl https://gist-ai.onrender.com/health
curl -X POST https://gist-ai.onrender.com/search \
  -H "Content-Type: application/json" \
  -d '{"query":"purple guy snapping his fingers","top_k":5}'

# Gateway (what the app calls) — proves the whole chain
curl https://gist-gateway.onrender.com/health
curl -X POST https://gist-gateway.onrender.com/api/search \
  -H "Content-Type: application/json" \
  -d '{"query":"a man who stays inside a dream","top_k":5}'
```
A successful `/api/search` returns TMDb-enriched movies with posters → gateway → AI → LanceDB → TMDb
all work. Empty `results` means the LanceDB table has no data (re-check ingestion).

---

## 4. Point the frontend at the gateway

In the `Recall/` frontend, set the API base URL to the gateway, e.g.
`EXPO_PUBLIC_API_URL=https://gist-gateway.onrender.com`, and call `/api/...`
(see [API_DOCS.md](./API_DOCS.md)).

---

## Gotchas for integration testing

- **Cold starts.** Free services sleep after ~15 min idle; the first request wakes them (~30–50 s
  each). The gateway waits up to 60 s for the AI service, so the *very first* search after both slept
  may still be slow or time out — hit each `/health` once to warm them, then search.
- **Embedding parity.** The deployed ONNX embedder (`fastembed`) produces vectors identical
  (cosine 1.0000) to the `sentence-transformers` build that created the LanceDB data, so no
  re-ingestion is needed. `ingest.py` also now uses `fastembed`.
- **Supabase storage bucket.** The avatar-upload route needs a public **`avatars`** bucket in
  Supabase Storage; create it if you haven't (the SQL migration doesn't).
- **Rotate leaked keys.** The old `ai/.env` was committed earlier in git history — rotate the LanceDB
  and TMDb keys before making the repo public.
- **Redeploys.** Render auto-deploys on every push to `main`.
