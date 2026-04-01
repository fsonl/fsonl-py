"""Common API tests — all language implementations should have equivalent tests.

Covers: dumps() rejection of invalid values/keys, valid serialization cases,
and dumps() with a list of entries.
"""

import pytest
from fsonl import dumps, loads, loads_raw, Schema


class TestSerializerRejectsInvalid:
    def test_nan(self):
        with pytest.raises(ValueError, match="NaN"):
            dumps({"type": "x", "v": float("nan")})

    def test_infinity(self):
        with pytest.raises(ValueError, match="Infinity"):
            dumps({"type": "x", "v": float("inf")})

    def test_neg_infinity(self):
        with pytest.raises(ValueError, match="Infinity"):
            dumps({"type": "x", "v": float("-inf")})

    def test_invalid_key_hyphen(self):
        with pytest.raises(ValueError, match="dry-run"):
            dumps({"type": "x", "dry-run": True})

    def test_invalid_key_dot(self):
        with pytest.raises(ValueError, match="a.b"):
            dumps({"type": "x", "a.b": True})

    def test_missing_type(self):
        with pytest.raises(ValueError, match="type"):
            dumps({"name": "test"})

    def test_unsupported_type(self):
        with pytest.raises(TypeError):
            dumps({"type": "x", "v": object()})


class TestSerializerValid:
    def test_string_value(self):
        assert dumps({"type": "log", "msg": "hello"}) == 'log(msg="hello")\n'

    def test_number_value(self):
        assert dumps({"type": "x", "v": 42}) == 'x(v=42)\n'

    def test_bool_value(self):
        assert dumps({"type": "x", "v": True}) == 'x(v=true)\n'

    def test_null_value(self):
        assert dumps({"type": "x", "v": None}) == 'x(v=null)\n'

    def test_array_value(self):
        assert dumps({"type": "x", "v": [1, 2]}) == 'x(v=[1, 2])\n'

    def test_round_trip_named(self):
        original = 'x(name="hello", count=42)\n'
        result = loads_raw(original)
        output = dumps(result.entries[0])
        re_parsed = loads_raw(output)
        assert result.entries[0].type == re_parsed.entries[0].type
        assert result.entries[0].named == re_parsed.entries[0].named

    def test_round_trip_positional_with_schema(self):
        schema = Schema.from_string('@schema x(a: string, --b: number)')
        entry = {"type": "x", "a": "hello", "b": 42}
        text = dumps(entry, schema=schema)
        assert text == '@schema x(a: string, --b: number)\nx("hello", b=42)\n'
        result = loads(text, schema=schema)
        assert result.entries[0] == entry


class TestDumpsList:
    """dumps() with a list of entries should serialize all of them."""

    def test_dumps_empty_list(self):
        assert dumps([]) == ''

    def test_dumps_single_item_list(self):
        assert dumps([{"type": "x", "v": 1}]) == 'x(v=1)\n'

    def test_dumps_multiple_entries(self):
        entries = [{"type": "a", "n": 1}, {"type": "b", "n": 2}]
        result = dumps(entries)
        assert result == 'a(n=1)\nb(n=2)\n'

    def test_dumps_list_with_schema(self):
        schema = Schema.from_string('@schema x(a: string)')
        entries = [{"type": "x", "a": "one"}, {"type": "x", "a": "two"}]
        result = dumps(entries, schema=schema, exclude_schema=True)
        assert result == 'x("one")\nx("two")\n'

    def test_dumps_list_with_schema_prepends_once(self):
        schema = Schema.from_string('@schema x(a: string)')
        entries = [{"type": "x", "a": "one"}, {"type": "x", "a": "two"}]
        result = dumps(entries, schema=schema)
        assert result.count('@schema') == 1
        assert result.startswith('@schema x(a: string)\n')
