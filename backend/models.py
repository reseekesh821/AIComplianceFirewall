from dataclasses import dataclass


@dataclass
class Violation:
    concept: str
    category: str
    action: str
    pattern_id: str
