"""Common API tests — all language implementations should have equivalent tests.

Covers: dumps() should error when schema is provided but the entry's type
is not defined in the schema. Silent fallback to named params is incorrect.
"""

import pytest
from fsonl import dumps, Schema


class TestDumpsUnknownTypeWithSchema:
    """When schema is explicitly provided, unknown types must error."""

    def test_unknown_type_errors(self):
        s = Schema.from_string('@schema x(a: string)')
        with pytest.raises(ValueError, match="(?i)unknown"):
            dumps({"type": "y", "a": "v"}, schema=s)

    def test_unknown_type_errors_even_with_allow_extra(self):
        s = Schema.from_string('@schema x(a: string)')
        with pytest.raises(ValueError, match="(?i)unknown"):
            dumps({"type": "y", "a": "v"}, schema=s, allow_extra=True)

    def test_known_type_ok(self):
        s = Schema.from_string('@schema x(a: string)')
        result = dumps({"type": "x", "a": "v"}, schema=s)
        assert 'x("v")' in result

    def test_multi_schema_unknown_type_errors(self):
        s = Schema.from_string('@schema a(x: string)\n@schema b(y: number)')
        with pytest.raises(ValueError, match="(?i)unknown"):
            dumps({"type": "c", "z": 1}, schema=s)

    def test_multi_schema_known_types_ok(self):
        s = Schema.from_string('@schema a(x: string)\n@schema b(y: number)')
        result = dumps({"type": "a", "x": "v"}, schema=s)
        assert 'a("v")' in result
