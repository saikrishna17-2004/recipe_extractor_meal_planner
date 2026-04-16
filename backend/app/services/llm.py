from __future__ import annotations

import json
import os
from dataclasses import dataclass

try:
    from langchain_google_genai import ChatGoogleGenerativeAI
except Exception:  # pragma: no cover - optional dependency
    ChatGoogleGenerativeAI = None

try:
    from langchain_core.messages import HumanMessage
except Exception:  # pragma: no cover - optional dependency
    HumanMessage = None

from ..config import get_settings
from .prompts import load_prompt


@dataclass
class LLMResult:
    raw_text: str
    data: dict | None = None


class RecipeLLM:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.api_key = self.settings.gemini_api_key or os.getenv('GEMINI_API_KEY')
        self.model_name = self.settings.gemini_model
        self.enabled = bool(self.api_key and ChatGoogleGenerativeAI)

    def _client(self):
        if not self.enabled:
            return None
        return ChatGoogleGenerativeAI(
            model=self.model_name,
            google_api_key=self.api_key,
            temperature=0.2,
        )

    def _invoke(self, prompt_name: str, payload: str) -> LLMResult | None:
        client = self._client()
        if not client or HumanMessage is None:
            return None
        prompt = load_prompt(prompt_name)
        message = HumanMessage(content=prompt.format(payload=payload))
        response = client.invoke([message])
        raw_text = getattr(response, 'content', '') or ''
        try:
            data = json.loads(raw_text)
        except Exception:
            data = None
        return LLMResult(raw_text=raw_text, data=data)

    def extract_recipe(self, payload: str) -> LLMResult | None:
        return self._invoke('extract_recipe.prompt.md', payload)

    def generate_nutrition(self, payload: str) -> LLMResult | None:
        return self._invoke('nutrition.prompt.md', payload)

    def generate_substitutions(self, payload: str) -> LLMResult | None:
        return self._invoke('substitutions.prompt.md', payload)

    def generate_meal_plan(self, payload: str) -> LLMResult | None:
        return self._invoke('meal_planner.prompt.md', payload)
