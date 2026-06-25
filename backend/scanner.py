import json
import re
from dataclasses import dataclass
from pathlib import Path

from config import Settings
from models import Violation
from semantic import semantic_scan


@dataclass
class RulePack:
    version: str
    updated_at: str
    rules: list[dict]


class RuleScanner:
    def __init__(self, rules_path: Path) -> None:
        self.rules_path = rules_path
        self._compiled: list[tuple[dict, re.Pattern]] = []
        self.pack = RulePack(version="0", updated_at="", rules=[])
        self.reload()

    def reload(self) -> None:
        data = json.loads(self.rules_path.read_text(encoding="utf-8"))
        self.pack = RulePack(
            version=data.get("version", "1.0.0"),
            updated_at=data.get("updated_at", ""),
            rules=data.get("rules", []),
        )
        compiled = []
        for rule in self.pack.rules:
            compiled.append((rule, re.compile(rule["pattern"])))
        self._compiled = compiled

    def save(self, data: dict) -> None:
        self.rules_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        self.reload()

    def scan(self, text: str) -> list[Violation]:
        seen: set[str] = set()
        hits: list[Violation] = []
        for rule, pattern in self._compiled:
            if not pattern.search(text):
                continue
            concept = rule["concept"]
            if concept in seen:
                continue
            seen.add(concept)
            hits.append(
                Violation(
                    concept=concept,
                    category=rule["category"],
                    action=rule["action"],
                    pattern_id=rule["id"],
                )
            )
        return hits


_scanner: RuleScanner | None = None


def get_scanner(rules_path: Path) -> RuleScanner:
    global _scanner
    if _scanner is None or _scanner.rules_path != rules_path:
        _scanner = RuleScanner(rules_path)
    return _scanner


def scan_with_rust(text: str) -> list[Violation]:
    import neuro_symbolic_validator

    return [
        Violation(
            concept=v.concept,
            category=v.category,
            action=v.action,
            pattern_id=v.pattern_id,
        )
        for v in neuro_symbolic_validator.scan_for_violations(text)
    ]


def _merge_violations(primary: list[Violation], extra: list[Violation]) -> list[Violation]:
    seen = {hit.concept for hit in primary}
    merged = list(primary)
    for hit in extra:
        if hit.concept in seen:
            continue
        merged.append(hit)
        seen.add(hit.concept)
    return merged


def scan_text(text: str, rules_path: Path, settings: Settings) -> list[Violation]:
    if settings.use_rust_engine:
        hits = scan_with_rust(text)
    else:
        hits = get_scanner(rules_path).scan(text)
    if settings.semantic_enabled:
        skip = {hit.concept for hit in hits}
        semantic_hits = semantic_scan(text, settings, skip_concepts=skip)
        hits = _merge_violations(hits, semantic_hits)
    return hits
