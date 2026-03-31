"""Common API tests — all language implementations should have equivalent tests.

Covers: loads/loads_raw behavior, schema duplicate rejection, ignore_inline_schema,
empty input, BOM handling, incomplete @schema directive, extra field policy edge,
and the any type.
"""

import pytest
from fsonl import loads, loads_raw, Schema
from fsonl._errors import ParseError, SchemaError, BindError
from fsonl._types import ExtraFieldPolicy


class TestRawSkipsCrossValidation:
    """loads_raw should not cross-validate @schema against code schema."""

    def test_loads_raw_no_cross_validation(self):
        text = '@schema x(a: number)\nx(1)\n'
        result = loads_raw(text)
        assert len(result.entries) == 1
        assert result.entries[0].type == 'x'

    def test_without_raw_cross_validation_fires(self):
        code = Schema.from_string('@schema x(a: string)')
        text = '@schema x(a: number)\nx(1)\n'
        with pytest.raises(SchemaError, match="type mismatch"):
            loads(text, schema=code)


class TestSchemaDuplicateRejection:
    """Schema.from_string/add should reject duplicate type definitions."""

    def test_from_string_duplicate(self):
        with pytest.raises(SchemaError, match="Duplicate"):
            Schema.from_string('@schema x(a: string)\n@schema x(b: number)')

    def test_add_duplicate(self):
        s = Schema.from_string('@schema x(a: string)')
        with pytest.raises(SchemaError, match="Duplicate"):
            s.add('@schema x(b: number)')


class TestIgnoreInlineSchema:
    """ignore_inline_schema=True should skip file @schema and not bind entries."""

    def test_loads_ignore_inline_schema(self):
        text = '@schema x(a: string)\nx("hello")\n'
        with pytest.raises(BindError, match="No schema for type"):
            loads(text, ignore_inline_schema=True)

    def test_loads_code_schema_overrides_file(self):
        code = Schema.from_string('@schema x(a: number)')
        text = '@schema x(a: number)\nx(42)\n'
        result = loads(text, schema=code)
        assert result.entries[0] == {"type": "x", "a": 42}

    def test_loads_ignore_file_with_code_schema(self):
        code = Schema.from_string('@schema x(a: number)')
        text = '@schema x(a: string)\nx(42)\n'
        result = loads(text, schema=code, ignore_inline_schema=True)
        assert result.entries[0] == {"type": "x", "a": 42}


class TestEmptyInput:
    """Empty input should return empty result with no entries."""

    def test_loads_empty_returns_no_entries(self):
        result = loads('')
        assert len(result.entries) == 0

    def test_loads_raw_empty_returns_no_entries(self):
        result = loads_raw('')
        assert len(result.entries) == 0


class TestBOMHandling:
    """BOM at start of input should be silently stripped."""

    def test_bom_only_input(self):
        result = loads_raw('\uFEFF')
        assert result.entries == []

    def test_bom_before_entry(self):
        result = loads_raw('\uFEFFx()\n')
        assert len(result.entries) == 1
        assert result.entries[0].type == 'x'


class TestIncompleteSchemaDirective:
    """Bare @schema without type name should raise ParseError."""

    def test_incomplete_schema_directive(self):
        with pytest.raises(ParseError, match="Incomplete @schema directive"):
            loads_raw('@schema\n')


class TestExtraFieldPolicyEdge:
    """ExtraFieldPolicy edge case: strip with no extras."""

    def test_strip_with_no_extras_is_same(self):
        schema = Schema.from_string('@schema x(a: string)')
        text = 'x("hello")\n'
        result = loads(text, schema=schema, extra_fields=ExtraFieldPolicy.STRIP)
        assert result[0] == {"type": "x", "a": "hello"}


class TestAnyType:
    """any type accepts any JSON value."""

    def test_any_accepts_bool(self):
        schema = Schema.from_string('@schema x(a: any)')
        text = 'x(true)\n'
        result = loads(text, schema=schema)
        assert result[0]["a"] is True

    def test_any_accepts_string(self):
        schema = Schema.from_string('@schema x(a: any)')
        text = 'x("hello")\n'
        result = loads(text, schema=schema)
        assert result[0]["a"] == "hello"

    def test_any_accepts_number(self):
        schema = Schema.from_string('@schema x(a: any)')
        text = 'x(42)\n'
        result = loads(text, schema=schema)
        assert result[0]["a"] == 42

    def test_any_accepts_null(self):
        schema = Schema.from_string('@schema x(a: any)')
        text = 'x(null)\n'
        result = loads(text, schema=schema)
        assert result[0]["a"] is None
