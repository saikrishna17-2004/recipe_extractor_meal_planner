from __future__ import annotations

from collections import defaultdict


def merge_shopping_lists(recipes: list[dict]) -> dict[str, list[str]]:
    merged: dict[str, set[str]] = defaultdict(set)
    for recipe in recipes:
        shopping_list = recipe.get('shopping_list') or {}
        for category, items in shopping_list.items():
            for item in items:
                merged[category].add(item)
    return {category: sorted(items) for category, items in sorted(merged.items())}
