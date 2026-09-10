# Deploying the Gist Backend

Two compute services to deploy. The data stores (**LanceDB Cloud**, **Supabase**) are already live,
so nothing to host there.

| Service | Folder | Host | Why |
| ------- | ------ | ---- | --- |
| AI microservice | `ai/` | **Hugging Face Docker Space** | Needs ~1 GB RAM for PyTorch + MiniLM; HF free tier gives 16 GB |
| Gateway API | `gateway/` | **Render** (free web service) | Lightweight Node app; the frontend talks only to this |

**Data flow once live:** `Frontend → Render (gateway) → HF Space (AI) → LanceDB` and `→ TMDb / Supabase`.

---

## 0. Prerequisites

- Accounts: [GitHub](https://github.com), [Hugging Face](https://huggingface.co), [Render](https://render.com).
- The backend repo pushes to **`github.com/lifeofstephanie/Recall`** (separate from the frontend repo
  `Parachurami/Recall`).
- Run all git commands from the **`backend/`** folder (that's where `.git` now lives).

### Commit & push the deploy changes first

Render and HF deploy from GitHub, so the code must be pushed.

```bash
cd backend
git add -A
git commit -m "Add deployment config (Docker Space + Render blueprint)"
git push origin main
```

---

## 1. AI microservice → Hugging Face Docker Space

### 1a. Create the Space
1. huggingface.co → **New → Space**.
2. Name it e.g. **`gist-ai`**, License optional, **SDK = Docker**, template **Blank**, visibility **Public**
   (private also works). Create.

### 1b. Add secrets
In the Space → **Settings → Variables and secrets**, add three **secrets**:

| Key | Value |
| --- | ----- |
| `LANCE_DB_URI` | your `db://…` URI |
| `LANCE_API_KEY` | your LanceDB Cloud key |
| `LANCE_TABLE_NAME` | `movie_quotes` (or whatever you ingested into) |

> `TMDB_API_KEY` is **not** needed here — it's only used by `ingest.py` locally. `EMBEDDING_MODEL`
> is optional (defaults to `sentence-transformers/all-MiniLM-L6-v2`).

### 1c. Push the `ai/` folder to the Space
The Space repo expects the Dockerfile at its **root**, but our Dockerfile is in `ai/`. Use
`git subtree` — it publishes only the git-tracked contents of `ai/` (so `venv/`, `.env`, and the
Kaggle data are automatically left out):

```bash
cd backend

# Create a write token at huggingface.co/settings/tokens, then:
git remote add space https://huggingface.co/spaces/<HF_USERNAME>/gist-ai

# Split the ai/ subfolder into a temp branch and force-push it as the Space's main
git subtree split --prefix=ai -b hf-deploy
git push space hf-deploy:main --force
git branch -D hf-deploy
```
When prompted for credentials: **username = your HF username, password = the write token.**

### 1d. Watch the build & test
- The Space **Logs** tab shows the Docker build (a few minutes — it installs PyTorch and bakes the
  model into the image). It's ready when logs show `🎬 Gist AI ready!`.
- Public URL: **`https://<HF_USERNAME>-gist-ai.hf.space`**
- Smoke test:
  ```bash
  curl https://<HF_USERNAME>-gist-ai.hf.space/health
  # {"status":"ok","service":"gist-ai"}

  curl -X POST https://<HF_USERNAME>-gist-ai.hf.space/search \
    -H "Content-Type: application/json" \
    -d '{"query":"purple guy snapping his fingers","top_k":5}'
  ```
  If `/search` returns results, the LanceDB table is populated and reachable. An empty `results`
  array means the table has no data (re-check that ingestion ran).

---

## 2. Gateway → Render

### 2a. Create the service from the blueprint
1. render.com → **New → Blueprint**.
2. Connect the **`lifeofstephanie/Recall`** repo. Render auto-detects `render.yaml` and proposes the
   **`gist-gateway`** web service (rootDir `gateway`, build `npm install && npm run build`, start
   `npm start`, health check `/health`).
3. Apply.

### 2b. Fill in the secret env vars
Render will prompt for every `sync: false` var. Set:

| Key | Value |
| --- | ----- |
| `SUPABASE_URL` | your Supabase project URL |
| `SUPABASE_ANON_KEY` | Supabase anon/public key |
| `SUPABASE_SERVICE_ROLE_KEY` | Supabase service-role key |
| `TMDB_API_KEY` | your TMDb key |
| `AI_SERVICE_URL` | **`https://<HF_USERNAME>-gist-ai.hf.space`** (no trailing slash) |
| `RESET_PASSWORD_URL` | your app's reset-password URL |

`NODE_ENV`, `TMDB_BASE_URL`, and the rate-limit vars are already set in `render.yaml`. Render provides
`PORT` automatically — the app reads it, so don't set it.

### 2c. Test
- URL: **`https://gist-gateway.onrender.com`** (Render shows the exact one).
  ```bash
  curl https://gist-gateway.onrender.com/health

  curl -X POST https://gist-gateway.onrender.com/api/search \
    -H "Content-Type: application/json" \
    -d '{"query":"a man who stays inside a dream","top_k":5}'
  ```
  A successful `/api/search` returns TMDb-enriched movies with posters — that proves the whole chain
  (gateway → HF AI → LanceDB → TMDb) works.

---

## 3. Point the frontend at the gateway

In the `Recall/` frontend, set the API base URL to the Render gateway URL, e.g.
`EXPO_PUBLIC_API_URL=https://gist-gateway.onrender.com`, and hit `/api/...` routes
(see [API_DOCS.md](./API_DOCS.md)).

---

## Gotchas for integration testing

- **Cold starts.** Both free tiers sleep when idle (Render ~15 min, HF after long inactivity). The
  first request wakes them and can take 30–60 s. The gateway waits up to 60 s for the AI service, so
  the *very first* search after both were asleep may still time out — hit each `/health` once to warm
  them, then search.
- **Supabase storage bucket.** The avatar-upload route needs a public **`avatars`** bucket in
  Supabase Storage; create it if you haven't (the SQL migration doesn't).
- **Rotate leaked keys.** The old `ai/.env` was committed earlier in git history — rotate the LanceDB
  and TMDb keys before making the repo public.
- **Redeploys.** Render auto-deploys on every push to `main`. For the HF Space, re-run the
  `git subtree split … && git push space … --force` block from step 1c.
