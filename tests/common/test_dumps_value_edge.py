"""Common API tests — all language implementations should have equivalent tests.

Covers: value edge cases that require API-level verification (loads_raw round-trip,
negative zero behavior). Basic value serialization is covered by E2E serialize/values.toml.
"""

from fsonl import dumps, loads_raw


class TestNegativeZero:
    """Negative zero behavior — cross-language pain point, not stable in text."""

    def test_negative_zero(self):
        result = dumps([{"type": "x", "v": -0.0}])
        rt = loads_raw(result)
        # -0.0 may serialize as 0 or -0.0; round-trip must be numerically equal
        assert rt.entries[0].named["v"] == 0


class TestStringRoundTripViaApi:
    """Strings that need loads_raw re-parsing to verify correctness."""

    def test_string_with_quotes(self):
        result = dumps([{"type": "x", "v": 'say "hi"'}])
        rt = loads_raw(result)
        assert rt.entries[0].named["v"] == 'say "hi"'

    def test_string_with_backslash(self):
        result = dumps([{"type": "x", "v": "a\\b"}])
        rt = loads_raw(result)
        assert rt.entries[0].named["v"] == "a\\b"

    def test_string_with_newline(self):
        result = dumps([{"type": "x", "v": "a\nb"}])
        rt = loads_raw(result)
        assert rt.entries[0].named["v"] == "a\nb"

    def test_string_with_tab(self):
        result = dumps([{"type": "x", "v": "a\tb"}])
        rt = loads_raw(result)
        assert rt.entries[0].named["v"] == "a\tb"
