import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

_BACKEND_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _BACKEND_DIR.parent


def _env_path(name: str, default: Path) -> str:
    raw = os.getenv(name)
    if not raw:
        return str(default)
    path = Path(raw)
    if path.is_absolute():
        return str(path)
    return str((_PROJECT_ROOT / path).resolve())


@dataclass(frozen=True)
class Settings:
    neo4j_uri: str
    neo4j_user: str
    neo4j_password: str
    sqlite_file: str
    rules_file: str
    ollama_url: str
    ollama_model: str
    llm_provider: str
    use_rust_engine: bool
    semantic_enabled: bool
    semantic_provider: str
    semantic_threshold: float
    semantic_concepts_file: str
    ollama_embed_url: str
    ollama_embed_model: str
    api_host: str
    api_port: int
    api_key: str | None


def get_settings() -> Settings:
    return Settings(
        neo4j_uri=os.getenv("NEO4J_URI", "neo4j://localhost:7687"),
        neo4j_user=os.getenv("NEO4J_USER", "neo4j"),
        neo4j_password=os.getenv("NEO4J_PASSWORD", "testpassword123"),
        sqlite_file=_env_path("SQLITE_FILE", _PROJECT_ROOT / "compliance.db"),
        rules_file=_env_path("RULES_FILE", _BACKEND_DIR / "rules" / "policy_rules.json"),
        ollama_url=os.getenv("OLLAMA_URL", "http://localhost:11434/api/generate"),
        ollama_model=os.getenv("OLLAMA_MODEL", "llama3.1:8b"),
        llm_provider=os.getenv("LLM_PROVIDER", "ollama").lower(),
        use_rust_engine=os.getenv("USE_RUST_ENGINE", "false").lower() == "true",
        semantic_enabled=os.getenv("SEMANTIC_ENABLED", "true").lower() == "true",
        semantic_provider=os.getenv("SEMANTIC_PROVIDER", "ollama").lower(),
        semantic_threshold=float(os.getenv("SEMANTIC_THRESHOLD", "0.82")),
        semantic_concepts_file=_env_path(
            "SEMANTIC_CONCEPTS_FILE",
            _BACKEND_DIR / "rules" / "semantic_concepts.json",
        ),
        ollama_embed_url=os.getenv(
            "OLLAMA_EMBED_URL", "http://localhost:11434/api/embeddings"
        ),
        ollama_embed_model=os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text"),
        api_host=os.getenv("API_HOST", "127.0.0.1"),
        api_port=int(os.getenv("API_PORT", "8000")),
        api_key=os.getenv("API_KEY") or None,
    )
