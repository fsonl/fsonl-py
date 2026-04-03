"""Common API tests — all language implementations should have equivalent tests.

Covers: variadic round-trip via API (loads → dumps → loads).
Basic variadic serialization is covered by E2E serialize/schema.toml.
"""

from fsonl import dumps, loads, Schema


class TestVariadicRoundTripApi:
    """Round-trip that chains API calls — not possible in E2E."""

    def test_positional_variadic_roundtrip(self):
        s = Schema.from_string('@schema x(level: string, *msg: string[])')
        entry = {"type": "x", "level": "info", "msg": ["a", "b"]}
        text = dumps([entry], schema=s, exclude_schema=True)
        result = loads(text, schema=s)
        assert result.entries[0] == entry
