from __future__ import annotations

import re
from collections import defaultdict

from .llm import RecipeLLM
from .scraper import ScrapedRecipePage, extract_context, scrape_recipe_page

ALLIUM_WORDS = {'garlic', 'onion', 'shallot', 'leek', 'scallion'}
DAIRY_WORDS = {'milk', 'cream', 'butter', 'cheese', 'yogurt', 'sour cream'}
PRODUCE_WORDS = {'tomato', 'lettuce', 'spinach', 'pepper', 'apple', 'banana', 'potato', 'carrot', 'basil', 'parsley', 'cilantro', 'lime', 'lemon'}
MEAT_WORDS = {'chicken', 'beef', 'pork', 'turkey', 'salmon', 'shrimp', 'bacon'}
PANTRY_WORDS = {'flour', 'sugar', 'salt', 'pepper', 'oil', 'rice', 'pasta', 'bread', 'vinegar', 'soy sauce'}
KNOWN_UNITS = {
    'slice', 'slices', 'tbsp', 'tablespoon', 'tablespoons', 'tsp', 'teaspoon', 'teaspoons',
    'cup', 'cups', 'oz', 'ounce', 'ounces', 'lb', 'lbs', 'pound', 'pounds', 'g', 'gram', 'grams',
    'kg', 'ml', 'l', 'pinch', 'pinches', 'dash', 'dashes', 'can', 'cans', 'clove', 'cloves',
    'package', 'packages', 'stick', 'sticks', 'piece', 'pieces'
}


class RecipeExtractor:
    def __init__(self) -> None:
        self.llm = RecipeLLM()

    def process_url(self, url: str, timeout: int = 20) -> dict:
        scraped = scrape_recipe_page(url, timeout=timeout)
        return self.process_scraped(scraped)

    def process_scraped(self, scraped: ScrapedRecipePage) -> dict:
        base = self._heuristic_extract(scraped)
        llm_data = self._llm_extract(scraped)
        merged = self._merge(base, llm_data)
        merged['url'] = scraped.url
        merged['raw_text'] = scraped.raw_text
        return merged

    def _llm_extract(self, scraped: ScrapedRecipePage) -> dict:
        payload = extract_context(scraped)
        payload_text = _json_dumps(payload)
        extracted: dict = {}
        try:
            llm_result = self.llm.extract_recipe(payload_text)
            if llm_result and isinstance(llm_result.data, dict):
                extracted.update(llm_result.data)
        except Exception:
            pass

        try:
            nutrition_result = self.llm.generate_nutrition(payload_text)
            if nutrition_result and isinstance(nutrition_result.data, dict):
                extracted['nutrition_estimate'] = nutrition_result.data
        except Exception:
            pass

        try:
            substitutions_result = self.llm.generate_substitutions(payload_text)
            if substitutions_result and isinstance(substitutions_result.data, dict):
                extracted['substitutions'] = substitutions_result.data.get('substitutions', [])
                extracted['shopping_list'] = substitutions_result.data.get('shopping_list', {})
                extracted['related_recipes'] = substitutions_result.data.get('related_recipes', [])
        except Exception:
            pass
        return extracted

    def _heuristic_extract(self, scraped: ScrapedRecipePage) -> dict:
        data = scraped.json_ld_recipe or {}
        title = data.get('title') or scraped.title or 'Untitled Recipe'
        ingredients_raw = data.get('ingredients_raw') or self._extract_ingredients_from_text(scraped.raw_text)
        ingredients = [self._parse_ingredient(value) for value in ingredients_raw]
        ingredients = [item for item in ingredients if item['item']]
        instructions = data.get('instructions') or self._extract_steps_from_text(scraped.raw_text)
        cuisine = data.get('cuisine') or self._infer_cuisine(title, scraped.raw_text)
        prep_time = self._normalize_duration(data.get('prep_time') or self._find_time(scraped.raw_text, 'prep'))
        cook_time = self._normalize_duration(data.get('cook_time') or self._find_time(scraped.raw_text, 'cook'))
        total_time = self._normalize_duration(data.get('total_time') or self._find_time(scraped.raw_text, 'total'))
        servings = data.get('servings') or self._infer_servings(scraped.raw_text)
        difficulty = self._infer_difficulty(total_time, instructions)
        nutrition = self._estimate_nutrition(ingredients, servings)
        substitutions = self._generate_substitutions(ingredients)
        shopping_list = self._build_shopping_list(ingredients)
        related_recipes = self._suggest_related_recipes(title, cuisine, ingredients)
        return {
            'title': title,
            'cuisine': cuisine,
            'prep_time': prep_time,
            'cook_time': cook_time,
            'total_time': total_time,
            'servings': servings,
            'difficulty': difficulty,
            'ingredients': ingredients,
            'instructions': instructions,
            'nutrition_estimate': nutrition,
            'substitutions': substitutions,
            'shopping_list': shopping_list,
            'related_recipes': related_recipes,
        }

    def _merge(self, base: dict, llm_data: dict) -> dict:
        merged = dict(base)
        for key, value in llm_data.items():
            if value not in (None, '', [], {}):
                merged[key] = value
        if not merged.get('ingredients'):
            merged['ingredients'] = []
        if not merged.get('instructions'):
            merged['instructions'] = []
        if not merged.get('nutrition_estimate'):
            merged['nutrition_estimate'] = self._estimate_nutrition(merged.get('ingredients', []), merged.get('servings'))
        if not merged.get('substitutions'):
            merged['substitutions'] = self._generate_substitutions(merged.get('ingredients', []))
        if not merged.get('shopping_list'):
            merged['shopping_list'] = self._build_shopping_list(merged.get('ingredients', []))
        if not merged.get('related_recipes'):
            merged['related_recipes'] = self._suggest_related_recipes(merged.get('title', ''), merged.get('cuisine'), merged.get('ingredients', []))
        return merged

    def _extract_ingredients_from_text(self, text: str) -> list[str]:
        candidate_lines: list[str] = []
        capture = False
        for line in text.splitlines():
            lowered = line.lower().strip()
            if 'ingredients' in lowered:
                capture = True
                continue
            if capture and any(token in lowered for token in ('instructions', 'directions', 'method', 'steps')):
                break
            if capture and line.strip():
                if len(line.strip()) < 160:
                    candidate_lines.append(line.strip())
        return candidate_lines[:30]

    def _extract_steps_from_text(self, text: str) -> list[str]:
        steps = []
        capture = False
        for line in text.splitlines():
            lowered = line.lower().strip()
            if any(token in lowered for token in ('instructions', 'directions', 'method', 'steps')):
                capture = True
                continue
            if capture and line.strip():
                if re.match(r'^(\d+\.|step\s+\d+)', line.strip(), re.I):
                    steps.append(re.sub(r'^\d+\.\s*', '', line.strip()))
                elif len(line.strip()) < 250:
                    steps.append(line.strip())
        return steps[:12] or [text.splitlines()[0][:160]]

    def _parse_ingredient(self, line: str) -> dict:
        cleaned = re.sub(r'\(.*?\)', '', line).strip()
        cleaned = re.sub(r'\b-\s*Note\s*\d+\)?$', '', cleaned, flags=re.I).strip()
        cleaned = re.sub(r'\s+', ' ', cleaned).strip(' ,;')
        mixed_match = re.match(r'^(?P<metric>\d+(?:\.\d+)?\s*[a-z]+)\s*/\s*(?P<primary>\d+(?:/\d+)?(?:\.\d+)?\s*[a-z]+)\s+(?P<item>.+)$', cleaned, re.I)
        if mixed_match:
            primary = mixed_match.group('primary').strip()
            item = mixed_match.group('item').strip(' ,;')
            quantity, unit = self._split_measurement(primary)
            return {'quantity': quantity, 'unit': unit, 'item': self._clean_ingredient_item(item)}

        tokens = cleaned.split()
        if not tokens:
            return {'quantity': None, 'unit': None, 'item': cleaned}

        quantity = None
        unit = None
        item_start = 0

        if self._looks_like_quantity(tokens[0]):
            quantity = tokens[0]
            item_start = 1
            if len(tokens) > 1 and self._normalize_unit(tokens[1]):
                unit = self._normalize_unit(tokens[1])
                item_start = 2
                if len(tokens) > 2 and self._normalize_unit(f"{tokens[1]} {tokens[2]}"):
                    unit = self._normalize_unit(f"{tokens[1]} {tokens[2]}")
                    item_start = 3

        item = ' '.join(tokens[item_start:]).strip() or cleaned
        return {'quantity': quantity, 'unit': unit, 'item': self._clean_ingredient_item(item)}

    def _split_measurement(self, measurement: str) -> tuple[str | None, str | None]:
        parts = measurement.split(maxsplit=1)
        if len(parts) == 1:
            return parts[0], None
        return parts[0], self._normalize_unit(parts[1]) or parts[1]

    def _clean_ingredient_item(self, item: str) -> str:
        item = re.sub(r'\b(?:chopped|minced|sliced|grated|softened|melted|optional|to taste)\b', '', item, flags=re.I)
        item = re.sub(r'\s*-\s*Note\s*\d+\)?', '', item, flags=re.I)
        item = re.sub(r'\)+\s*$', '', item).strip()
        item = re.sub(r'\s+', ' ', item).strip(' ,;')
        return item

    def _infer_cuisine(self, title: str, text: str) -> str:
        content = f'{title} {text}'.lower()
        mapping = {
            'Italian': ['pasta', 'parmesan', 'marinara', 'risotto', 'caprese'],
            'Mexican': ['taco', 'salsa', 'cilantro', 'queso', 'enchilada'],
            'Indian': ['garam masala', 'curry', 'turmeric', 'naan', 'paneer'],
            'Asian': ['soy sauce', 'sesame', 'ginger', 'miso', 'noodles'],
            'American': ['burger', 'sandwich', 'bbq', 'mac and cheese', 'grilled cheese'],
        }
        for cuisine, words in mapping.items():
            if any(word in content for word in words):
                return cuisine
        return 'American'

    def _find_time(self, text: str, label: str) -> str | None:
        patterns = {
            'prep': re.compile(r'prep(?:aration)?\s*time\s*[:\-]?\s*([^\n\r]+)', re.I),
            'cook': re.compile(r'cook\s*time\s*[:\-]?\s*([^\n\r]+)', re.I),
            'total': re.compile(r'total\s*time\s*[:\-]?\s*([^\n\r]+)', re.I),
        }
        match = patterns[label].search(text)
        if match:
            return match.group(1).strip()
        return None

    def _normalize_duration(self, value: str | None) -> str | None:
        if not value:
            return None
        value = value.strip()
        iso_match = re.fullmatch(r'P(?:T)?(?:(\d+)H)?(?:(\d+)M)?', value, re.I)
        if iso_match:
            hours = int(iso_match.group(1) or 0)
            minutes = int(iso_match.group(2) or 0)
            total_minutes = hours * 60 + minutes
            if total_minutes == 0:
                return value
            if total_minutes < 60:
                return f'{total_minutes} mins'
            if total_minutes % 60 == 0:
                return f'{total_minutes // 60} hr'
            return f'{total_minutes // 60} hr {total_minutes % 60} mins'
        return value

    def _looks_like_quantity(self, token: str) -> bool:
        return bool(re.fullmatch(r'\d+(?:[\-/]\d+)?(?:\.\d+)?', token))

    def _normalize_unit(self, token: str) -> str | None:
        normalized = token.lower().strip().rstrip('.')
        if normalized in KNOWN_UNITS:
            if normalized.endswith('s') and normalized[:-1] in KNOWN_UNITS:
                return normalized[:-1]
            return normalized
        return None

    def _infer_servings(self, text: str) -> int | None:
        match = re.search(r'servings?\s*[:\-]?\s*(\d+)', text, re.I)
        if match:
            return int(match.group(1))
        return None

    def _infer_difficulty(self, total_time: str | None, instructions: list[str]) -> str:
        if total_time:
            minutes = self._minutes_from_text(total_time)
            if minutes is not None:
                if minutes <= 20 and len(instructions) <= 5:
                    return 'easy'
                if minutes <= 45:
                    return 'medium'
                return 'hard'
        if len(instructions) <= 4:
            return 'easy'
        if len(instructions) <= 8:
            return 'medium'
        return 'hard'

    def _minutes_from_text(self, value: str) -> int | None:
        match = re.search(r'(\d+)\s*(?:min|minute)', value, re.I)
        if match:
            return int(match.group(1))
        return None

    def _estimate_nutrition(self, ingredients: list[dict], servings: int | None) -> dict:
        servings = servings or 2
        calories = 120 + sum(self._ingredient_calories(item['item']) for item in ingredients)
        protein = 4 + sum(1.5 for item in ingredients if self._is_protein(item['item']))
        carbs = 10 + sum(3 for item in ingredients if self._is_carb(item['item']))
        fat = 6 + sum(2 for item in ingredients if self._is_fat(item['item']))
        per_serving = max(1, servings)
        return {
            'calories': round(calories / per_serving),
            'protein': f'{round(protein / per_serving)}g',
            'carbs': f'{round(carbs / per_serving)}g',
            'fat': f'{round(fat / per_serving)}g',
        }

    def _ingredient_calories(self, item: str) -> int:
        content = item.lower()
        if any(word in content for word in DAIRY_WORDS):
            return 80
        if any(word in content for word in MEAT_WORDS):
            return 120
        if any(word in content for word in {'oil', 'butter'}):
            return 100
        if any(word in content for word in {'bread', 'rice', 'pasta', 'flour'}):
            return 90
        if any(word in content for word in PRODUCE_WORDS):
            return 20
        return 35

    def _is_protein(self, item: str) -> bool:
        content = item.lower()
        return any(word in content for word in MEAT_WORDS | {'egg', 'beans', 'tofu', 'lentil', 'cheese'})

    def _is_carb(self, item: str) -> bool:
        content = item.lower()
        return any(word in content for word in {'bread', 'rice', 'pasta', 'flour', 'potato', 'sugar'})

    def _is_fat(self, item: str) -> bool:
        content = item.lower()
        return any(word in content for word in {'butter', 'oil', 'cream', 'cheese', 'avocado', 'nuts'})

    def _generate_substitutions(self, ingredients: list[dict]) -> list[str]:
        substitutions: list[str] = []
        ingredient_texts = ' '.join(item['item'].lower() for item in ingredients)
        if 'butter' in ingredient_texts:
            substitutions.append('Replace butter with olive oil for a dairy-free version.')
        if any(word in ingredient_texts for word in ALLIUM_WORDS):
            substitutions.append('Use garlic-infused oil or roasted shallots to soften sharp allium flavor.')
        if 'white bread' in ingredient_texts:
            substitutions.append('Use whole wheat bread instead of white bread for more fiber.')
        if 'cheddar' in ingredient_texts:
            substitutions.append('Swap cheddar with mozzarella for a milder, stretchier finish.')
        if 'milk' in ingredient_texts:
            substitutions.append('Use unsweetened oat milk as a plant-based alternative to milk.')
        if 'egg' in ingredient_texts:
            substitutions.append('Replace each egg with a flax egg if you need an egg-free option.')
        if not substitutions:
            substitutions.append('Use a neutral oil or plant-based substitute for any dairy ingredient if needed.')
        return substitutions[:3]

    def _build_shopping_list(self, ingredients: list[dict]) -> dict[str, list[str]]:
        grouped: dict[str, list[str]] = defaultdict(list)
        for ingredient in ingredients:
            item = ingredient['item']
            category = self._categorize(item)
            if item not in grouped[category]:
                grouped[category].append(item)
        return dict(sorted(grouped.items()))

    def _categorize(self, item: str) -> str:
        content = item.lower()
        if any(word in content for word in DAIRY_WORDS):
            return 'dairy'
        if any(word in content for word in PRODUCE_WORDS):
            return 'produce'
        if any(word in content for word in MEAT_WORDS):
            return 'protein'
        if any(word in content for word in PANTRY_WORDS):
            return 'pantry'
        if any(word in content for word in {'spice', 'pepper', 'paprika', 'cumin', 'oregano', 'basil'}):
            return 'spices'
        return 'other'

    def _suggest_related_recipes(self, title: str, cuisine: str | None, ingredients: list[dict]) -> list[str]:
        title_text = title.lower()
        base = []
        if 'sandwich' in title_text or 'grilled cheese' in title_text:
            base = ['Tomato Soup', 'French Onion Grilled Cheese', 'Caprese Sandwich']
        elif cuisine == 'Italian':
            base = ['Garlic Bread', 'Caesar Salad', 'Pasta Primavera']
        elif cuisine == 'Mexican':
            base = ['Fresh Pico de Gallo', 'Black Bean Tacos', 'Mexican Street Corn']
        elif cuisine == 'Indian':
            base = ['Cucumber Raita', 'Vegetable Biryani', 'Garlic Naan']
        else:
            base = ['Simple Side Salad', 'Roasted Vegetables', 'Homemade Dip']
        return base[:3]


def _json_dumps(payload: dict) -> str:
    import json

    return json.dumps(payload, ensure_ascii=True, indent=2)
