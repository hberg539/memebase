import pytest

from memebase.ai import build_prompt, parse_ai_response


class TestBuildPrompt:
    def test_substitutes_tags(self):
        result = build_prompt("Use these tags: {tags}", ["funny", "cat"])
        assert result == "Use these tags: funny, cat"

    def test_empty_tags(self):
        result = build_prompt("Tags: {tags}", [])
        assert result == "Tags: "

    def test_no_placeholder(self):
        result = build_prompt("No placeholder here", ["a"])
        assert result == "No placeholder here"


class TestParseAiResponse:
    def test_plain_json(self):
        result = parse_ai_response('{"name": "test", "tags": ["a"]}')
        assert result == {"name": "test", "tags": ["a"]}

    def test_fenced_json(self):
        result = parse_ai_response('```json\n{"name": "test"}\n```')
        assert result == {"name": "test"}

    def test_fenced_no_lang(self):
        result = parse_ai_response('```\n{"name": "test"}\n```')
        assert result == {"name": "test"}

    def test_invalid_json(self):
        with pytest.raises(Exception):
            parse_ai_response("not json at all")
