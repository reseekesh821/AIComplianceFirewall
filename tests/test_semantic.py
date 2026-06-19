from dataclasses import replace
from pathlib import Path

from scanner import scan_text


def test_semantic_catches_paraphrase(mock_settings):
    text = "You cannot lose money on this investment — profits are certain."
    hits = scan_text(text, Path(mock_settings.rules_file), mock_settings)
    concepts = {hit.concept for hit in hits}
    assert "Guaranteed Returns" in concepts
    assert any(hit.pattern_id.startswith("semantic_") for hit in hits)


def test_semantic_skips_when_regex_already_matched(mock_settings):
    text = "guaranteed return with zero risk"
    hits = scan_text(text, Path(mock_settings.rules_file), mock_settings)
    semantic_ids = [hit.pattern_id for hit in hits if hit.pattern_id.startswith("semantic_")]
    assert semantic_ids == []


def test_semantic_disabled_falls_back_to_regex(mock_settings):
    settings = replace(mock_settings, semantic_enabled=False)
    text = "You cannot lose money on this investment — profits are certain."
    hits = scan_text(text, Path(settings.rules_file), settings)
    assert hits == []
