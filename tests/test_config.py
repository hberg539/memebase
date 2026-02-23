import copy

from config import _DEFAULTS, _deep_merge


def test_empty_user_config():
    """Empty user config returns all defaults intact."""
    result = _deep_merge(_DEFAULTS, {})
    assert result == _DEFAULTS


def test_full_user_config_overrides():
    """User supplies every key — all defaults replaced."""
    user = {
        "grid": {"thumbnail_size": 300, "page_size": 80},
        "ai": {"enabled": True, "parallel": 8},
    }
    result = _deep_merge(_DEFAULTS, user)
    assert result == user


def test_old_config_missing_section():
    """User has [grid] only — [ai] defaults filled in."""
    user = {"grid": {"thumbnail_size": 150, "page_size": 25}}
    result = _deep_merge(_DEFAULTS, user)
    assert result["grid"] == user["grid"]
    assert result["ai"] == _DEFAULTS["ai"]


def test_old_config_missing_key():
    """User has [ai] with only 'enabled' — 'parallel' default filled in."""
    user = {"ai": {"enabled": True}}
    result = _deep_merge(_DEFAULTS, user)
    assert result["ai"]["enabled"] is True
    assert result["ai"]["parallel"] == _DEFAULTS["ai"]["parallel"]


def test_user_extra_keys_preserved():
    """User keys not in defaults (e.g. ai.model, ai.prompt) kept as-is."""
    user = {"ai": {"enabled": True, "model": "gpt-4", "prompt": "describe"}}
    result = _deep_merge(_DEFAULTS, user)
    assert result["ai"]["model"] == "gpt-4"
    assert result["ai"]["prompt"] == "describe"


def test_user_override_single_value():
    """User overrides grid.page_size = 100, rest stays default."""
    user = {"grid": {"page_size": 100}}
    result = _deep_merge(_DEFAULTS, user)
    assert result["grid"]["page_size"] == 100
    assert result["grid"]["thumbnail_size"] == _DEFAULTS["grid"]["thumbnail_size"]


def test_nested_merge_does_not_clobber():
    """Overriding one key in a section doesn't delete sibling keys."""
    user = {"ai": {"parallel": 10}}
    result = _deep_merge(_DEFAULTS, user)
    assert result["ai"]["parallel"] == 10
    assert "enabled" in result["ai"]
    assert result["ai"]["enabled"] == _DEFAULTS["ai"]["enabled"]


def test_defaults_not_mutated():
    """Calling _deep_merge doesn't modify the _DEFAULTS dict."""
    snapshot = copy.deepcopy(_DEFAULTS)
    _deep_merge(_DEFAULTS, {"grid": {"page_size": 999}, "ai": {"enabled": True}})
    assert _DEFAULTS == snapshot
