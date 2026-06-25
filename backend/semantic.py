import json
import math
import re
from dataclasses import dataclass
from pathlib import Path

import requests

from config import Settings
from models import Violation


@dataclass
class SemanticConcept:
    id: str
    concept: str
    category: str
    action: str
    phrases: list[str]


class OllamaEmbedder:
    def __init__(self, url: str, model: str) -> None:
        self.url = url
        self.model = model

    def embed(self, text: str) -> list[float]:
        response = requests.post(
            self.url,
            json={"model": self.model, "prompt": text},
            timeout=60,
        )
        response.raise_for_status()
        return response.json()["embedding"]

    def ping(self) -> bool:
        try:
            base = self.url.replace("/api/embeddings", "")
            requests.get(base, timeout=3)
            return True
        except requests.RequestException:
            return False


class MockEmbedder:
    """Deterministic overlap scorer for tests — no network or model download."""

    def embed(self, text: str) -> list[float]:
        tokens = text.lower().split()
        size = 32
        vector = [0.0] * size
        for token in tokens:
            vector[hash(token) % size] += 1.0
        norm = math.sqrt(sum(v * v for v in vector))
        if norm == 0:
            return vector
        return [v / norm for v in vector]

    def ping(self) -> bool:
        return True


def cosine_similarity(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def get_embedder(settings: Settings):
    if settings.semantic_provider == "mock":
        return MockEmbedder()
    return OllamaEmbedder(settings.ollama_embed_url, settings.ollama_embed_model)


def load_semantic_concepts(path: Path) -> list[SemanticConcept]:
    data = json.loads(path.read_text(encoding="utf-8"))
    concepts = []
    for item in data.get("concepts", []):
        concepts.append(
            SemanticConcept(
                id=item["id"],
                concept=item["concept"],
                category=item["category"],
                action=item["action"],
                phrases=item.get("phrases", []),
            )
        )
    return concepts


def _sentence_chunks(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+|\n+", text.strip())
    chunks = [part.strip() for part in parts if part.strip()]
    if not chunks and text.strip():
        return [text.strip()]
    if len(text.strip()) > 40:
        chunks.append(text.strip())
    return chunks or [text]


class SemanticScanner:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.concepts_path = Path(settings.semantic_concepts_file)
        self.concepts = load_semantic_concepts(self.concepts_path)
        self.embedder = get_embedder(settings)
        self._phrase_vectors: list[tuple[SemanticConcept, str, list[float]]] = []
        self._ready = False

    def warm_up(self) -> None:
        if self._ready:
            return
        for concept in self.concepts:
            for phrase in concept.phrases:
                vector = self.embedder.embed(phrase)
                self._phrase_vectors.append((concept, phrase, vector))
        self._ready = True

    def ping(self) -> bool:
        return self.embedder.ping()

    def scan(self, text: str, skip_concepts: set[str] | None = None) -> list[Violation]:
        if not text.strip():
            return []
        skip = skip_concepts or set()
        self.warm_up()
        hits: list[Violation] = []
        seen: set[str] = set()
        for chunk in _sentence_chunks(text):
            chunk_vector = self.embedder.embed(chunk)
            best_by_concept: dict[str, tuple[float, SemanticConcept]] = {}
            for concept, _phrase, phrase_vector in self._phrase_vectors:
                if concept.concept in skip or concept.concept in seen:
                    continue
                score = cosine_similarity(chunk_vector, phrase_vector)
                prev = best_by_concept.get(concept.concept)
                if prev is None or score > prev[0]:
                    best_by_concept[concept.concept] = (score, concept)
            for concept_name, (score, concept) in best_by_concept.items():
                if score < self.settings.semantic_threshold:
                    continue
                seen.add(concept_name)
                hits.append(
                    Violation(
                        concept=concept.concept,
                        category=concept.category,
                        action=concept.action,
                        pattern_id=concept.id,
                    )
                )
        return hits


_scanner: SemanticScanner | None = None


def get_semantic_scanner(settings: Settings) -> SemanticScanner:
    global _scanner
    path = Path(settings.semantic_concepts_file)
    if (
        _scanner is None
        or _scanner.settings.semantic_concepts_file != settings.semantic_concepts_file
        or _scanner.settings.semantic_provider != settings.semantic_provider
        or _scanner.settings.semantic_threshold != settings.semantic_threshold
    ):
        _scanner = SemanticScanner(settings)
    return _scanner


def semantic_scan(
    text: str,
    settings: Settings,
    skip_concepts: set[str] | None = None,
) -> list[Violation]:
    if not settings.semantic_enabled:
        return []
    try:
        return get_semantic_scanner(settings).scan(text, skip_concepts=skip_concepts)
    except Exception:
        return []
