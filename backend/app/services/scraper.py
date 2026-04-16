from __future__ import annotations

import json
from dataclasses import dataclass
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

from .parser import extract_json_ld, extract_relevant_text, find_title, parse_json_ld_recipe


@dataclass
class ScrapedRecipePage:
    url: str
    title: str | None
    raw_html: str
    raw_text: str
    json_ld_recipe: dict | None


def validate_recipe_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme not in {'http', 'https'} or not parsed.netloc:
        raise ValueError('Please provide a valid recipe URL starting with http:// or https://')


def fetch_page(url: str, timeout: int = 20) -> str:
    headers = {
        'User-Agent': 'Mozilla/5.0 (RecipeExtractor/1.0; +https://example.com)',
        'Accept-Language': 'en-US,en;q=0.9',
    }
    response = requests.get(url, headers=headers, timeout=timeout)
    response.raise_for_status()
    return response.text


def scrape_recipe_page(url: str, timeout: int = 20) -> ScrapedRecipePage:
    validate_recipe_url(url)
    html = fetch_page(url, timeout=timeout)
    soup = BeautifulSoup(html, 'html.parser')
    title = find_title(soup)
    json_ld = extract_json_ld(soup)
    json_ld_recipe = parse_json_ld_recipe(json_ld[0]) if json_ld else None
    raw_text = extract_relevant_text(soup)
    return ScrapedRecipePage(
        url=url,
        title=title or (json_ld_recipe or {}).get('title'),
        raw_html=html,
        raw_text=raw_text,
        json_ld_recipe=json_ld_recipe,
    )


def extract_context(scraped: ScrapedRecipePage) -> dict:
    context: dict = {
        'url': scraped.url,
        'title': scraped.title,
        'raw_text': scraped.raw_text,
    }
    if scraped.json_ld_recipe:
        context['json_ld_recipe'] = scraped.json_ld_recipe
    return context
