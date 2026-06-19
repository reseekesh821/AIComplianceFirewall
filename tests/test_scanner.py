from scanner import RuleScanner


def test_json_scanner_finra(rules_path):
    scanner = RuleScanner(rules_path)
    hits = scanner.scan("guaranteed return with zero risk")
    concepts = {h.concept for h in hits}
    assert "Guaranteed Returns" in concepts
    assert "Risk-Free Investment" in concepts
