# Vercel deployment

This repository supports the existing Docker deployment and a native FastAPI deployment on Vercel. The React frontend is built by `build_vercel.py` and included in the Python function. No Docker daemon is needed on Vercel.

## Configuration

- Import the private `baotduong91/cleanviet` repository into the intended Vercel account/team.
- Framework: FastAPI. Entrypoint: `app.main:app`.
- Build command: `python build_vercel.py` (declared in `pyproject.toml`).
- Python: 3.12, declared by `requires-python`.
- Database: set `DATABASE_URL` using a hosted PostgreSQL connection string; localhost cannot be reached from Vercel. Standard `postgresql://` and `postgres://` URLs are normalized for SQLAlchemy asyncpg. `sslmode` is translated to certificate-verified TLS.
- Vercel-generated preview and production hostnames are accepted through `VERCEL_URL` and `VERCEL_PROJECT_PRODUCTION_URL`. Custom domains require adding their exact hostnames to comma-separated `ALLOWED_HOSTS`.
- Optional: set `GOOGLE_PLACES_API_KEY` for the existing review feature.

Configure secret values in Vercel, never in Git or chat. `.env` variants and `.vercel/` are excluded from Git. The repository contains application source, not a dump of local family meal data.

## Database initialization

After linking the Vercel project and verifying the hosted database environment, run `python seed_data.py` against the hosted `DATABASE_URL` once. It applies the additive canvas migration under a PostgreSQL lock. Database migrations do not run on every preview build. Use separate preview and production databases so preview tests cannot change production meals.

## Verification before assigning the production URL

Check the deployed homepage, `/api/health`, ingredient parsing, saving/reloading a canvas, checkbox persistence and optional provider failure handling. Verify the selected account/team and deployment protection policy for this single-household app before publishing its URL.

The local Docker database is preserved. A new hosted database starts with an empty canvas; local meal records are not automatically copied.
