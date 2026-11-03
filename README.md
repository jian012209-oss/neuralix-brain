# Neuralix Brain

Neuralix Brain is the private server-side intelligence API for Neuralix AI. It uses FastAPI, Neon/PostgreSQL with pgvector, local FastEmbed embeddings, and Gemini for generation.

## Deploy on Render

This repository includes a Dockerfile and `render.yaml`. Create a Render Web Service from this repository and use the Docker runtime. Set these environment variables in Render:

- `DATABASE_URL` — Neon PostgreSQL connection string. Use the pooled connection string if your Neon setup recommends it.
- `BRAIN_API_KEY` — a long, random secret shared only by the Neuralix AI backend and this service.
- `GEMINI_API_KEY` — Gemini API key.
- `GEMINI_MODEL` — optional; defaults in the app to `gemini-3.1-flash-lite`.

Do not put `BRAIN_API_KEY`, `DATABASE_URL`, or `GEMINI_API_KEY` in browser JavaScript, mobile app code, public repositories, or client-side environment variables.

## Database

Run `database/schema.sql` against the Neon database before using the API. The schema uses the `vector` extension and 384-dimensional embeddings.

## Security boundary — important

Every protected route currently authenticates the calling server using `X-Brain-Api-Key`. The `user_id` in request bodies and paths is an application-level identifier, not proof of identity. Therefore:

1. Only call this API from your trusted Neuralix AI server.
2. Your Neuralix AI server must authenticate each end user first.
3. Derive `user_id` from the verified server-side session/JWT, never from a browser-supplied value.
4. Never expose the Brain API key to the browser or a downloadable app.
5. Keep `/docs` and `/redoc` inaccessible to the public in production, or disable them in the app configuration after testing.

A shared API key alone does not provide end-user authentication or tenant isolation if untrusted clients can call the API.

## Health checks

- `GET /` — service identity/status
- `GET /health` — process health
- `GET /db-health` — database connectivity check

## Embeddings

The service uses `BAAI/bge-small-en-v1.5` through FastEmbed. The first embedding request downloads the model, so the first request can be slower and the service needs enough memory and disk space. Embeddings are 384 dimensions and must match the `vector(384)` database column.

## Operational notes

- Free hosting/database tiers have usage, sleep, storage, and compute limits; they are not guaranteed to be permanently free.
- Rotate secrets immediately if they are ever exposed.
- Check Render logs for startup, model-download, database, and Gemini errors.
