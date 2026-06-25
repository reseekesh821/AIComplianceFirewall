from pathlib import Path

import pytest

from config import Settings

_BACKEND_RULES = Path(__file__).resolve().parent.parent / "backend" / "rules"


@pytest.fixture
def rules_path(tmp_path):
    src = _BACKEND_RULES / "policy_rules.json"
    dest = tmp_path / "policy_rules.json"
    dest.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
    return dest


@pytest.fixture
def semantic_path(tmp_path):
    src = _BACKEND_RULES / "semantic_concepts.json"
    dest = tmp_path / "semantic_concepts.json"
    dest.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
    return dest


@pytest.fixture
def mock_settings(rules_path, semantic_path):
    return Settings(
        neo4j_uri="neo4j://localhost:7687",
        neo4j_user="neo4j",
        neo4j_password="test",
        sqlite_file=":memory:",
        rules_file=str(rules_path),
        ollama_url="http://localhost:11434/api/generate",
        ollama_model="llama3.1:8b",
        llm_provider="mock",
        use_rust_engine=False,
        semantic_enabled=True,
        semantic_provider="mock",
        semantic_threshold=0.82,
        semantic_concepts_file=str(semantic_path),
        ollama_embed_url="http://localhost:11434/api/embeddings",
        ollama_embed_model="nomic-embed-text",
        api_host="127.0.0.1",
        api_port=8000,
        api_key=None,
    )
