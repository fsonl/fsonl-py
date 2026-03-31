"""Common API tests — all language implementations should have equivalent tests.

Covers: schema validation errors NOT covered by E2E tests.
- variadic non-array type
- schema positional after named
- unknown type keyword
- incomplete @schema directive
- bare carriage return
"""

import pytest
from fsonl import loads_raw, Schema
from fsonl._errors import ParseError


class TestSchemaValidationErrors:
    """Schema errors not covered by E2E."""

    def test_variadic_non_array_type(self):
        with pytest.raises(ParseError):
            Schema.from_string('@schema x(*a: string)')

    def test_schema_positional_after_named(self):
        with pytest.raises(ParseError):
            Schema.from_string('@schema x(--a: string, b: number)')

    def test_unknown_type_keyword(self):
        with pytest.raises(ParseError):
            Schema.from_string('@schema x(a: integer)')


class TestParserEdgeErrors:
    """Parser edge errors not covered by E2E."""

    def test_incomplete_schema_no_space(self):
        with pytest.raises(ParseError):
            loads_raw('@schemaX(a: string)\n')

    def test_bare_cr(self):
        with pytest.raises(ParseError):
            loads_raw('x(1)\rx(2)\n')
