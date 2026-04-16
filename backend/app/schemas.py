from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field, HttpUrl


class IngredientItem(BaseModel):
    quantity: str | None = None
    unit: str | None = None
    item: str


class RecipeBase(BaseModel):
    url: HttpUrl
    title: str
    cuisine: str | None = None
    prep_time: str | None = None
    cook_time: str | None = None
    total_time: str | None = None
    servings: int | None = None
    difficulty: str | None = None
    ingredients: list[IngredientItem] = Field(default_factory=list)
    instructions: list[str] = Field(default_factory=list)
    nutrition_estimate: dict[str, str | int] = Field(default_factory=dict)
    substitutions: list[str] = Field(default_factory=list)
    shopping_list: dict[str, list[str]] = Field(default_factory=dict)
    related_recipes: list[str] = Field(default_factory=list)
    raw_text: str | None = None


class RecipeCreate(RecipeBase):
    pass


class RecipeRead(RecipeBase):
    id: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class RecipeSummary(BaseModel):
    id: int
    url: str
    title: str
    cuisine: str | None = None
    difficulty: str | None = None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class ExtractRequest(BaseModel):
    url: HttpUrl


class MealPlanRequest(BaseModel):
    recipe_ids: list[int]


class MealPlanResponse(BaseModel):
    recipe_ids: list[int]
    shopping_list: dict[str, list[str]]
    recipes: list[RecipeSummary]
