from functools import lru_cache
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse
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
        url = self.database_url
        if url.startswith('postgres://'):
            url = url.replace('postgres://', 'postgresql+psycopg2://', 1)
        elif url.startswith('postgresql://') and '+psycopg2' not in url:
            url = url.replace('postgresql://', 'postgresql+psycopg2://', 1)

        if not url.startswith('postgresql+psycopg2://'):
            return url

        parsed = urlparse(url)
        query = dict(parse_qsl(parsed.query, keep_blank_values=True))
        if 'sslmode' not in query:
            query['sslmode'] = 'require'
        return urlunparse(parsed._replace(query=urlencode(query)))


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
