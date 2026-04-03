"""Common API tests — all language implementations should have equivalent tests.

Covers: dumps() API-level behavior that E2E cannot test:
- single dict rejection (API interface)
- NaN/Infinity/unsupported type rejection (cannot express in JSONL)
- round-trip via loads_raw/loads (API chaining)
- schema header emission count
"""

import pytest
from fsonl import dumps, loads, loads_raw, Schema


class TestDumpsRejectsSingleDict:
    """dumps() must only accept a list, not a single dict."""

    def test_single_dict_raises_type_error(self):
        with pytest.raises(TypeError):
            dumps({"type": "x", "v": 1})


class TestSerializerRejectsNonJsonValues:
    """Values that cannot be expressed in JSONL — E2E cannot cover these."""

    def test_nan(self):
        with pytest.raises(ValueError, match="NaN"):
            dumps([{"type": "x", "v": float("nan")}])

    def test_infinity(self):
        with pytest.raises(ValueError, match="Infinity"):
            dumps([{"type": "x", "v": float("inf")}])

    def test_neg_infinity(self):
        with pytest.raises(ValueError, match="Infinity"):
            dumps([{"type": "x", "v": float("-inf")}])

    def test_unsupported_type(self):
        with pytest.raises(TypeError):
            dumps([{"type": "x", "v": object()}])


class TestRoundTripViaApi:
    """Round-trip tests that chain API calls (not possible in E2E)."""

    def test_round_trip_named(self):
        original = 'x(name="hello", count=42)\n'
        result = loads_raw(original)
        output = dumps([result.entries[0]])
        re_parsed = loads_raw(output)
        assert result.entries[0].type == re_parsed.entries[0].type
        assert result.entries[0].named == re_parsed.entries[0].named

    def test_round_trip_positional_with_schema(self):
        schema = Schema.from_string('@schema x(a: string, --b: number)')
        entry = {"type": "x", "a": "hello", "b": 42}
        text = dumps([entry], schema=schema)
        assert text == '@schema x(a: string, --b: number)\nx("hello", b=42)\n'
        result = loads(text, schema=schema)
        assert result.entries[0] == entry


class TestDumpsListSchemaApi:
    """Schema-related list behavior only testable via API."""

    def test_dumps_list_with_schema_excludes(self):
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
