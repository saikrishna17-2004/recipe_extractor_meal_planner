from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from .database import Base, engine
from .config import get_settings


settings = get_settings()
JSONType = JSONB if 'postgresql' in settings.database_url else JSON


class Recipe(Base):
    __tablename__ = 'recipes'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    url: Mapped[str] = mapped_column(String(2048), unique=True, index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    cuisine: Mapped[str | None] = mapped_column(String(120), nullable=True)
    prep_time: Mapped[str | None] = mapped_column(String(50), nullable=True)
    cook_time: Mapped[str | None] = mapped_column(String(50), nullable=True)
    total_time: Mapped[str | None] = mapped_column(String(50), nullable=True)
    servings: Mapped[int | None] = mapped_column(Integer, nullable=True)
    difficulty: Mapped[str | None] = mapped_column(String(20), nullable=True)
    ingredients: Mapped[list] = mapped_column(JSONType, nullable=False, default=list)
    instructions: Mapped[list] = mapped_column(JSONType, nullable=False, default=list)
    nutrition_estimate: Mapped[dict] = mapped_column(JSONType, nullable=False, default=dict)
    substitutions: Mapped[list] = mapped_column(JSONType, nullable=False, default=list)
    shopping_list: Mapped[dict] = mapped_column(JSONType, nullable=False, default=dict)
    related_recipes: Mapped[list] = mapped_column(JSONType, nullable=False, default=list)
    raw_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False, index=True)
