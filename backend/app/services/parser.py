from __future__ import annotations

import re
from typing import Iterable

from bs4 import BeautifulSoup

TIME_PATTERNS = [
    re.compile(r'(?P<label>prep(?:aration)?|cook|total)\s*time\s*[:\-]?\s*(?P<value>[^\n\r]+)', re.I),
    re.compile(r'(?P<label>prep|cook|total)\s*[:\-]\s*(?P<value>[^\n\r]+)', re.I),
]


def clean_text(value: str) -> str:
    return re.sub(r'\s+', ' ', value).strip()


def text_from_soup(soup: BeautifulSoup) -> str:
    for tag in soup(['script', 'style', 'noscript', 'svg']):
        tag.decompose()
    text = soup.get_text(separator='\n')
    lines = [clean_text(line) for line in text.splitlines()]
    return '\n'.join(line for line in lines if line)


def extract_json_ld(soup: BeautifulSoup) -> list[dict]:
    recipes: list[dict] = []
    for script in soup.select('script[type="application/ld+json"]'):
        raw = script.string or script.get_text(strip=True)
        if not raw:
            continue
        try:
            import json

            payload = json.loads(raw)
        except Exception:
            continue
        if isinstance(payload, list):
            candidates = payload
        else:
            candidates = [payload]
        for candidate in candidates:
            if isinstance(candidate, dict) and _is_recipe_type(candidate.get('@type')):
                recipes.append(candidate)
            elif isinstance(candidate, dict) and isinstance(candidate.get('@graph'), list):
                recipes.extend([item for item in candidate['@graph'] if isinstance(item, dict) and _is_recipe_type(item.get('@type'))])
    return recipes


def _is_recipe_type(value: object) -> bool:
    if isinstance(value, str):
        return value.lower() == 'recipe'
    if isinstance(value, list):
        return any(isinstance(item, str) and item.lower() == 'recipe' for item in value)
    return False


def find_title(soup: BeautifulSoup) -> str | None:
    meta = soup.find('meta', attrs={'property': 'og:title'})
    if meta and meta.get('content'):
        return clean_text(meta['content'])
    heading = soup.find(['h1', 'title'])
    if heading:
        return clean_text(heading.get_text(' ', strip=True))
    return None


def extract_time_value(data: dict, keys: Iterable[str]) -> str | None:
    for key in keys:
        if data.get(key):
            value = data[key]
            if isinstance(value, str):
                return clean_text(value)
    return None


def parse_instructions(data: dict) -> list[str]:
    instructions = data.get('recipeInstructions') or []
    steps: list[str] = []
    for item in instructions:
        if isinstance(item, str):
            steps.append(clean_text(item))
        elif isinstance(item, dict) and item.get('text'):
            steps.append(clean_text(item['text']))
    return [step for step in steps if step]


def parse_ingredients(data: dict) -> list[str]:
    ingredients = data.get('recipeIngredient') or []
    if isinstance(ingredients, list):
        return [clean_text(item) for item in ingredients if isinstance(item, str) and item.strip()]
    return []


def parse_servings(data: dict) -> int | None:
    value = data.get('recipeYield')
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        match = re.search(r'\d+', value)
        if match:
            return int(match.group())
    return None


def parse_json_ld_recipe(data: dict) -> dict:
    return {
        'title': _normalize_json_ld_value(data.get('name')),
        'cuisine': _normalize_json_ld_value(data.get('recipeCuisine')),
        'prep_time': extract_time_value(data, ['prepTime']),
        'cook_time': extract_time_value(data, ['cookTime']),
        'total_time': extract_time_value(data, ['totalTime']),
        'servings': parse_servings(data),
        'ingredients_raw': parse_ingredients(data),
        'instructions': parse_instructions(data),
    }


def _normalize_json_ld_value(value: object) -> str | None:
    if isinstance(value, str):
        return clean_text(value) or None
    if isinstance(value, list):
        items = [clean_text(str(item)) for item in value if str(item).strip()]
        return clean_text(', '.join(items)) or None
    if value is None:
        return None
    return clean_text(str(value)) or None


def extract_relevant_text(soup: BeautifulSoup, limit: int = 12000) -> str:
    blocks: list[str] = []
    for selector in ['article', 'main', 'body']:
        nodes = soup.select(selector)
        for node in nodes[:1]:
            blocks.append(text_from_soup(node))
            break
        if blocks:
            break
    if not blocks:
        blocks.append(text_from_soup(soup))
    text = '\n'.join(blocks)
    return text[:limit]
