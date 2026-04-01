"""Common API tests — all language implementations should have equivalent tests.

Covers: value edge cases in serialization — empty strings, unicode, escapes,
nested structures, number edge cases. Verifies dumps → loads_raw round-trip.
"""

import pytest
from fsonl import dumps, loads_raw


class TestStringEdgeCases:
    """String value edge cases in serialization."""

    def test_empty_string(self):
        result = dumps([{"type": "x", "v": ""}])
        assert 'v=""' in result
        rt = loads_raw(result)
        assert rt.entries[0].named["v"] == ""

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

    def test_unicode_korean(self):
        result = dumps([{"type": "x", "v": "한글"}])
        rt = loads_raw(result)
        assert rt.entries[0].named["v"] == "한글"

    def test_unicode_emoji(self):
        result = dumps([{"type": "x", "v": "🎉"}])
        rt = loads_raw(result)
        assert rt.entries[0].named["v"] == "🎉"

    def test_unicode_cjk(self):
        result = dumps([{"type": "x", "v": "日本語"}])
        rt = loads_raw(result)
        assert rt.entries[0].named["v"] == "日本語"


class TestNumberEdgeCases:
    """Number value edge cases in serialization."""

    def test_zero(self):
        result = dumps([{"type": "x", "v": 0}])
        assert "v=0" in result

    def test_negative_zero(self):
        result = dumps([{"type": "x", "v": -0.0}])
        rt = loads_raw(result)
        # -0.0 may serialize as 0 or -0.0; round-trip must be numerically equal
        assert rt.entries[0].named["v"] == 0

    def test_negative_number(self):
        result = dumps([{"type": "x", "v": -42}])
        assert "v=-42" in result

    def test_float(self):
        result = dumps([{"type": "x", "v": 3.14}])
        rt = loads_raw(result)
        assert abs(rt.entries[0].named["v"] - 3.14) < 1e-10

    def test_large_integer(self):
        result = dumps([{"type": "x", "v": 9007199254740992}])
        rt = loads_raw(result)
        assert rt.entries[0].named["v"] == 9007199254740992

    def test_small_float(self):
        result = dumps([{"type": "x", "v": 1e-10}])
        rt = loads_raw(result)
        assert abs(rt.entries[0].named["v"] - 1e-10) < 1e-20


class TestNullEdgeCases:
    """Null value edge cases."""

    def test_null_standalone(self):
        result = dumps([{"type": "x", "v": None}])
        assert "v=null" in result

    def test_null_in_array(self):
        result = dumps([{"type": "x", "v": [None, 1, None]}])
        assert "v=[null, 1, null]" in result

    def test_null_in_object(self):
        result = dumps([{"type": "x", "v": {"k": None}}])
        rt = loads_raw(result)
        assert rt.entries[0].named["v"] == {"k": None}


class TestEmptyContainers:
    """Empty array and object edge cases."""

    def test_empty_array(self):
        result = dumps([{"type": "x", "v": []}])
        assert "v=[]" in result
        rt = loads_raw(result)
        assert rt.entries[0].named["v"] == []

    def test_empty_object(self):
        result = dumps([{"type": "x", "v": {}}])
        rt = loads_raw(result)
        assert rt.entries[0].named["v"] == {}


class TestNestedStructures:
    """Nested arrays and objects."""

    def test_nested_array(self):
        result = dumps([{"type": "x", "v": [[1, 2], [3, 4]]}])
        rt = loads_raw(result)
        assert rt.entries[0].named["v"] == [[1, 2], [3, 4]]

    def test_nested_object(self):
        result = dumps([{"type": "x", "v": {"a": {"b": 1}}}])
        rt = loads_raw(result)
        assert rt.entries[0].named["v"] == {"a": {"b": 1}}

    def test_deeply_nested(self):
        result = dumps([{"type": "x", "v": {"a": {"b": {"c": [1, [2]]}}}}])
        rt = loads_raw(result)
        assert rt.entries[0].named["v"] == {"a": {"b": {"c": [1, [2]]}}}

    def test_mixed_nested(self):
        val = [{"k": [1, None, "x"]}, "y", [True, False]]
        result = dumps([{"type": "x", "v": val}])
        rt = loads_raw(result)
        assert rt.entries[0].named["v"] == val

    def test_object_in_array(self):
        val = [{"a": 1}, {"b": 2}]
        result = dumps([{"type": "x", "v": val}])
        rt = loads_raw(result)
        assert rt.entries[0].named["v"] == val

    def test_array_in_object(self):
        val = {"items": [1, 2, 3], "name": "test"}
        result = dumps([{"type": "x", "v": val}])
        rt = loads_raw(result)
        assert rt.entries[0].named["v"] == val
