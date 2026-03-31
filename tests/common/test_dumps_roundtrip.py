"""Common API tests — all language implementations should have equivalent tests.

Covers: round-trip tests — loads → dumps → loads should produce equivalent entries.
Tests preserve mode, raw mode, and schema-bound mode round-trips.
"""

import pytest
from fsonl import loads, loads_raw, dumps, Schema
from fsonl._types import ExtraFieldPolicy


class TestLoadsPreserveDumpsRoundtrip:
    """loads(preserve) -> dumps(allow_extra=True) -> loads should match."""

    def test_simple_named_roundtrip(self):
        schema = Schema.from_string('@schema x(a: string)')
        text = '@schema x(a: string)\nx("hello")\n'
        result = loads(text, schema=schema, extra_fields=ExtraFieldPolicy.PRESERVE)
        entries = result.entries
        assert len(entries) == 1

        roundtripped = dumps(entries, schema=schema, allow_extra=True, exclude_schema=True)
        result2 = loads(roundtripped, schema=schema)
        assert result2.entries[0]["a"] == entries[0]["a"]
        assert result2.entries[0]["type"] == entries[0]["type"]

    def test_multiple_entries_roundtrip(self):
        schema = Schema.from_string('@schema x(a: string, --b: number)')
        entries_in = [
            {"type": "x", "a": "foo", "b": 1},
            {"type": "x", "a": "bar", "b": 2},
        ]
        text = dumps(entries_in, schema=schema, exclude_schema=True)
        result = loads(text, schema=schema)
        assert result.entries[0] == entries_in[0]
        assert result.entries[1] == entries_in[1]


class TestRawDumpsRoundtrip:
    """loads_raw -> dumps raw entry -> loads_raw should match."""

    def test_positional_roundtrip(self):
        original = 'log("hello", 42)\n'
        result = loads_raw(original)
        entry = result.entries[0]
        serialized = dumps(entry)
        result2 = loads_raw(serialized)
        assert result2.entries[0].type == entry.type
        assert result2.entries[0].positional == entry.positional
        assert result2.entries[0].named == entry.named

    def test_named_roundtrip(self):
        original = 'x(name="alice", count=3)\n'
        result = loads_raw(original)
        entry = result.entries[0]
        serialized = dumps(entry)
        result2 = loads_raw(serialized)
        assert result2.entries[0].named == entry.named

    def test_empty_entry_roundtrip(self):
        original = 'evt()\n'
        result = loads_raw(original)
        entry = result.entries[0]
        serialized = dumps(entry)
        assert serialized == 'evt()\n'
        result2 = loads_raw(serialized)
        assert result2.entries[0].type == 'evt'
        assert result2.entries[0].positional == []
        assert result2.entries[0].named == {}


class TestSchemaBindRoundtrip:
    """loads with schema -> dumps with schema -> loads should match."""

    def test_string_param_roundtrip(self):
        schema = Schema.from_string('@schema user(name: string, --role: string)')
        entry = {"type": "user", "name": "alice", "role": "admin"}
        text = dumps(entry, schema=schema, exclude_schema=True)
        result = loads(text, schema=schema)
        assert result.entries[0] == entry

    def test_number_param_roundtrip(self):
        schema = Schema.from_string('@schema point(x: number, y: number)')
        entry = {"type": "point", "x": 3.14, "y": 2.72}
        text = dumps(entry, schema=schema, exclude_schema=True)
        result = loads(text, schema=schema)
        assert result.entries[0] == entry

    def test_bool_param_roundtrip(self):
        schema = Schema.from_string('@schema flag(--enabled: bool)')
        entry = {"type": "flag", "enabled": True}
        text = dumps(entry, schema=schema, exclude_schema=True)
        result = loads(text, schema=schema)
        assert result.entries[0] == entry

    def test_array_param_roundtrip(self):
        schema = Schema.from_string('@schema tags(*items: string[])')
        entry = {"type": "tags", "items": ["a", "b", "c"]}
        text = dumps(entry, schema=schema, exclude_schema=True)
        result = loads(text, schema=schema)
        assert result.entries[0] == entry

    def test_optional_absent_roundtrip(self):
        schema = Schema.from_string('@schema x(a: string, --b?: number)')
        entry = {"type": "x", "a": "ok"}
        text = dumps(entry, schema=schema, exclude_schema=True)
        result = loads(text, schema=schema)
        assert result.entries[0]["a"] == "ok"
        assert "b" not in result.entries[0]

    def test_schema_header_included_roundtrip(self):
        schema = Schema.from_string('@schema x(a: string)')
        entry = {"type": "x", "a": "hello"}
        text = dumps(entry, schema=schema)
        # Should be parseable without providing schema separately
        result = loads(text)
        assert result.entries[0] == entry
