from abc import ABC, abstractmethod

import requests

from config import Settings


class LLMProvider(ABC):
    @abstractmethod
    def generate(self, prompt: str) -> str:
        pass


class OllamaProvider(LLMProvider):
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def generate(self, prompt: str) -> str:
        payload = {
            "model": self.settings.ollama_model,
            "prompt": prompt,
            "stream": False,
        }
        response = requests.post(self.settings.ollama_url, json=payload, timeout=120)
        response.raise_for_status()
        return response.json().get("response", "")


class MockLLMProvider(LLMProvider):
    """Deterministic provider for tests and demos without Ollama."""

    def generate(self, prompt: str) -> str:
        lower = prompt.lower()
        if "guarantee" in lower and "return" in lower:
            return "This portfolio offers a guaranteed return with zero risk."
        if "guaranteed cure" in lower or ("guarantee" in lower and "cure" in lower):
            return "This supplement is a guaranteed cure for chronic illness."
        if "definitive diagnosis" in lower:
            return "Based on symptoms, the definitive diagnosis is diabetes."
        return (
            "Investing involves risk, and past performance is not "
            "indicative of future results."
        )


def get_llm(settings: Settings) -> LLMProvider:
    if settings.llm_provider == "mock":
        return MockLLMProvider()
    return OllamaProvider(settings)
