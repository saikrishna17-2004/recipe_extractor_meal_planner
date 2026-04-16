from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import Recipe


def create_recipe(db: Session, recipe_data: dict) -> Recipe:
    recipe = Recipe(**recipe_data)
    db.add(recipe)
    db.commit()
    db.refresh(recipe)
    return recipe


def get_recipe_by_id(db: Session, recipe_id: int) -> Recipe | None:
    return db.get(Recipe, recipe_id)


def get_recipe_by_url(db: Session, url: str) -> Recipe | None:
    stmt = select(Recipe).where(Recipe.url == url)
    return db.execute(stmt).scalar_one_or_none()


def list_recipes(db: Session) -> list[Recipe]:
    stmt = select(Recipe).order_by(Recipe.created_at.desc())
    return list(db.execute(stmt).scalars().all())


def list_recipe_summaries(db: Session) -> list[dict]:
    stmt = (
        select(Recipe.id, Recipe.url, Recipe.title, Recipe.cuisine, Recipe.difficulty, Recipe.created_at)
        .order_by(Recipe.created_at.desc())
    )
    rows = db.execute(stmt).all()
    return [
        {
            'id': row.id,
            'url': row.url,
            'title': row.title,
            'cuisine': row.cuisine,
            'difficulty': row.difficulty,
            'created_at': row.created_at,
        }
        for row in rows
    ]


def get_recipes_by_ids(db: Session, recipe_ids: list[int]) -> list[Recipe]:
    if not recipe_ids:
        return []
    stmt = select(Recipe).where(Recipe.id.in_(recipe_ids))
    recipes = db.execute(stmt).scalars().all()
    recipes_by_id = {recipe.id: recipe for recipe in recipes}
    return [recipes_by_id[recipe_id] for recipe_id in recipe_ids if recipe_id in recipes_by_id]
