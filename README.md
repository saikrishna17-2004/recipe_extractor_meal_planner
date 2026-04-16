# Recipe Extractor & Meal Planner

A FastAPI application with a minimal browser UI for extracting recipe data from blog URLs, storing results in PostgreSQL, and building a simple meal planner from saved recipes.

## Features

- Tab 1: extract recipe data from a blog URL
- Tab 2: view saved recipes and open a detail modal
- Optional meal planner: merge shopping lists from selected saved recipes
- PostgreSQL-backed persistence via SQLAlchemy
- BeautifulSoup scraping with an LLM-friendly prompt pipeline
- Prompt templates stored in `prompts/`
- Example inputs and outputs stored in `sample_data/`

## Stack

- Backend: FastAPI
- Database: PostgreSQL
- Frontend: Vanilla HTML, CSS, and JavaScript served by FastAPI
- Scraping: BeautifulSoup + requests
- LLM support: Gemini via LangChain, with a deterministic fallback when no API key is present

## Setup

1. Create a virtual environment.
2. Install dependencies:

```bash
pip install -r backend/requirements.txt
```

3. Set environment variables in a `.env` file at the workspace root:

```env
DATABASE_URL=postgresql+psycopg2://postgres:postgres@localhost:5432/recipe_planner
GEMINI_API_KEY=your_key_here
GEMINI_MODEL=gemini-1.5-flash
```

4. Start the API:

```bash
uvicorn backend.app.main:app --reload
```

5. Open `http://127.0.0.1:8000`.

## Endpoints

- `GET /health` - health check
- `POST /api/extract` - extract and store a recipe from a URL
- `GET /api/recipes` - list saved recipes
- `GET /api/recipes/{recipe_id}` - fetch a stored recipe in full
- `POST /api/meal-plan` - merge shopping lists for selected recipe IDs

### Example request

```bash
curl -X POST http://127.0.0.1:8000/api/extract \
  -H "Content-Type: application/json" \
  -d "{\"url\":\"https://www.allrecipes.com/recipe/23891/grilled-cheese-sandwich/\"}"
```

## Prompt Templates

The LangChain prompt templates used by the extraction pipeline are stored here:

- `prompts/extract_recipe.prompt.md`
- `prompts/nutrition.prompt.md`
- `prompts/substitutions.prompt.md`
- `prompts/meal_planner.prompt.md`

## Sample Data

- `sample_data/urls.txt` contains URLs used for testing.
- `sample_data/*.json` contains example API outputs.

## Notes

- The application uses PostgreSQL when `DATABASE_URL` points to Postgres.
- If no Gemini key is configured, the extractor falls back to a deterministic parsing and heuristic generation path so the app still runs end to end.
- Some recipe websites block automated scraping and may return 401/403. In those cases, extraction is rejected and no history row is created.
- Screenshots were not generated in this workspace; capture them after running the app for submission.

## Publish (GitHub + Render)

This repository is deployment-ready with `Dockerfile` and `render.yaml`.

1. Push your code to GitHub (already done for this project).
2. In Render, choose New + Blueprint and select this repository.
3. Render will detect `render.yaml` and create:
  - a web service for the FastAPI app
  - a managed PostgreSQL database
4. In the Render dashboard, set `GEMINI_API_KEY` in the web service environment variables.
5. Deploy. Once finished, open your Render URL and verify:
  - `/health` returns `{"status":"ok"}`
  - UI loads at `/`

### Environment Variables for Production

- `DATABASE_URL` (auto-provided by Render via `render.yaml`)
- `GEMINI_API_KEY` (optional but recommended)
- `GEMINI_MODEL` (default: `gemini-1.5-flash`)

If `DATABASE_URL` is missing on Render, the app now fails fast at startup with a clear error instead of silently using local SQLite.

### Notes for Hosted Postgres URLs

The app normalizes `postgres://` and `postgresql://` URLs to the SQLAlchemy psycopg2 format automatically, so no manual URL rewriting is required.
