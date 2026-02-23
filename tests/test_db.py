from db import _normalize_tags


def test_lowercase_and_strip():
    assert _normalize_tags(["  Hello ", "WORLD"]) == {"hello", "world"}


def test_dedup():
    assert _normalize_tags(["a", "A", "a"]) == {"a"}


def test_empty_filtered():
    assert _normalize_tags(["", "  ", "ok"]) == {"ok"}


def test_all_empty():
    assert _normalize_tags(["", " "]) == set()
