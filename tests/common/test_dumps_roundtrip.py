"""Common API tests — all language implementations should have equivalent tests.

Covers: round-trip tests that use API-only features (ExtraFieldPolicy.PRESERVE,
schema header re-parsing). Basic round-trips are covered by E2E serialize/roundtrip.toml.
"""

from fsonl import loads, dumps, Schema
from fsonl._types import ExtraFieldPolicy


class TestLoadsPreserveDumpsRoundtrip:
    """loads(preserve) -> dumps(allow_extra=True) -> loads — API-only feature."""

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


class TestSchemaHeaderIncludedRoundtrip:
    """dumps with schema header should be self-contained (parseable without separate schema)."""

    def test_schema_header_included_roundtrip(self):
        schema = Schema.from_string('@schema x(a: string)')
        entry = {"type": "x", "a": "hello"}
        text = dumps([entry], schema=schema)
        # Should be parseable without providing schema separately
        result = loads(text)
        assert result.entries[0] == entry
