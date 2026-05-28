# Gist Gateway — Node.js API

The traffic controller for the Gist app. Handles auth (via Supabase), routes search queries to the Python AI microservice, enriches results with TMDb metadata, and persists search history.

## Quick Start

```bash
# 1. Install dependencies
npm install

# 2. Set up environment
cp .env.example .env
# Fill in your keys in .env

# 3. Run Supabase migration
# Open Supabase Dashboard > SQL Editor > paste supabase_migration.sql > Run

# 4. Start the server
npm run dev
```

## API Endpoints

### Auth

| Method | Path                 | Body                  | Auth         |
| ------ | -------------------- | --------------------- | ------------ |
| POST   | `/api/auth/register` | `{ email, password }` | None         |
| POST   | `/api/auth/login`    | `{ email, password }` | None         |
| POST   | `/api/auth/logout`   | —                     | Bearer token |
| GET    | `/api/auth/me`       | —                     | Bearer token |

### Search

| Method | Path          | Body                | Auth     |
| ------ | ------------- | ------------------- | -------- |
| POST   | `/api/search` | `{ query, top_k? }` | Optional |

### History

| Method | Path               | Auth     |
| ------ | ------------------ | -------- |
| GET    | `/api/history`     | Required |
| DELETE | `/api/history/:id` | Required |
| DELETE | `/api/history`     | Required |

## Environment Variables

See `.env.example` for all required variables.

## Project Structure

```
src/
├── index.js              # Express app entry point
├── config/
│   └── supabase.js       # Supabase service role client
├── middleware/
│   ├── auth.middleware.js # JWT verification + requireAuth guard
│   └── error.middleware.js
├── routes/
│   ├── auth.routes.js
│   ├── search.routes.js
│   └── history.routes.js
├── controllers/
│   ├── auth.controller.js
│   ├── search.controller.js
│   └── history.controller.js
└── services/
    ├── ai.service.js     # Python AI microservice client
    └── tmdb.service.js   # TMDb API client
```
