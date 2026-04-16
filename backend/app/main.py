from __future__ import annotations

from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

from .config import get_settings
from .crud import create_recipe, get_recipe_by_id, get_recipe_by_url, get_recipes_by_ids, list_recipe_summaries, list_recipes
from .database import Base, engine, get_db
from .models import Recipe
from .schemas import ExtractRequest, MealPlanRequest, MealPlanResponse, RecipeRead, RecipeSummary
from .services.extractor import RecipeExtractor
from .services.planner import merge_shopping_lists

settings = get_settings()
BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / 'static'
app = FastAPI(title=settings.app_name)
app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

app.mount('/static', StaticFiles(directory=str(STATIC_DIR)), name='static')
extractor = RecipeExtractor()


@app.on_event('startup')
def create_tables() -> None:
    Base.metadata.create_all(bind=engine)


@app.get('/')
def index():
    return FileResponse(str(STATIC_DIR / 'index.html'))


@app.get('/health')
def health():
    return {'status': 'ok'}


@app.post('/api/extract', response_model=RecipeRead)
def extract_recipe(request: ExtractRequest, db: Session = Depends(get_db)):
    existing = get_recipe_by_url(db, str(request.url))
    if existing:
        return existing
    try:
        recipe_data = extractor.process_url(str(request.url), timeout=settings.request_timeout_seconds)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f'Unable to process recipe URL: {exc}') from exc

    stored = create_recipe(db, recipe_data)
    return stored


@app.get('/api/recipes', response_model=list[RecipeSummary])
def get_recipes(db: Session = Depends(get_db)):
    return list_recipe_summaries(db)


@app.get('/api/recipes/{recipe_id}', response_model=RecipeRead)
def get_recipe(recipe_id: int, db: Session = Depends(get_db)):
    recipe = get_recipe_by_id(db, recipe_id)
    if not recipe:
        raise HTTPException(status_code=404, detail='Recipe not found')
    return recipe


@app.post('/api/meal-plan', response_model=MealPlanResponse)
def meal_plan(request: MealPlanRequest, db: Session = Depends(get_db)):
    recipes = get_recipes_by_ids(db, request.recipe_ids)
    if not recipes:
        raise HTTPException(status_code=404, detail='No matching recipes found')
    merged = merge_shopping_lists([{'shopping_list': recipe.shopping_list} for recipe in recipes])
    summaries = [RecipeSummary.model_validate(recipe).model_dump() for recipe in recipes]
    return MealPlanResponse(recipe_ids=request.recipe_ids, shopping_list=merged, recipes=summaries)
