from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8', extra='ignore')

    app_name: str = 'Recipe Extractor & Meal Planner'
    database_url: str = 'sqlite:///./recipe_planner.db'
    gemini_api_key: str | None = None
    gemini_model: str = 'gemini-1.5-flash'
    request_timeout_seconds: int = 20

    @property
    def normalized_database_url(self) -> str:
        if self.database_url.startswith('postgres://'):
            return self.database_url.replace('postgres://', 'postgresql+psycopg2://', 1)
        if self.database_url.startswith('postgresql://') and '+psycopg2' not in self.database_url:
            return self.database_url.replace('postgresql://', 'postgresql+psycopg2://', 1)
        return self.database_url


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
