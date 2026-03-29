"""Serializer validation tests for raw entry dict path: type name, key, and reserved word checks."""

import pytest
from fsonl import dumps


class TestFormatRawRejectsInvalid:
    def test_invalid_type_name_hyphen(self):
        with pytest.raises(ValueError, match="bad-name"):
            dumps({"type": "bad-name", "positional": [], "named": {}})

    def test_invalid_type_name_space(self):
        with pytest.raises(ValueError, match="bad name"):
            dumps({"type": "bad name", "positional": [], "named": {}})

    def test_invalid_type_name_digit_start(self):
        with pytest.raises(ValueError, match="123"):
            dumps({"type": "123", "positional": [], "named": {}})

    def test_invalid_named_key_hyphen(self):
        with pytest.raises(ValueError, match="dry-run"):
            dumps({"type": "ok", "positional": [], "named": {"dry-run": True}})

    def test_reserved_type_key(self):
        with pytest.raises(ValueError, match="type"):
            dumps({"type": "ok", "positional": [], "named": {"type": "x"}})


class TestFormatRawValid:
    def test_simple(self):
        assert dumps({"type": "log", "positional": ["hello"], "named": {}}) == 'log("hello")\n'

    def test_with_named(self):
        assert dumps({"type": "x", "positional": [], "named": {"name": "ok"}}) == 'x(name="ok")\n'

    def test_empty(self):
        assert dumps({"type": "x", "positional": [], "named": {}}) == 'x()\n'
