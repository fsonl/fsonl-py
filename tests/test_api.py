"""API behavior tests: raw mode, bind mode, schema duplicates, streaming, ignore_inline_schema."""

import io
import pytest
from fsonl import loads, loads_raw, load_raw, Schema
from fsonl._api import iter_entries, iter_raw
from fsonl._errors import SchemaError


class TestRawSkipsCrossValidation:
    """loads_raw should not cross-validate @schema against code schema."""

    def test_loads_raw_no_cross_validation(self):
        text = '@schema x(a: number)\nx(1)\n'
        result = loads_raw(text)
        assert len(result.entries) == 1
        assert result.entries[0]["type"] == 'x'

    def test_iter_raw_no_cross_validation(self):
        text = '@schema x(a: number)\nx(1)\n'
        entries = list(iter_raw(text))
        assert len(entries) == 1
        assert entries[0]["type"] == 'x'

    def test_without_raw_cross_validation_fires(self):
        code = Schema.from_string('@schema x(a: string)')
        text = '@schema x(a: number)\nx(1)\n'
        with pytest.raises(SchemaError, match="type mismatch"):
            loads(text, schema=code)


class TestLoadRaw:
    """load_raw should parse file objects without binding."""

    def test_load_raw_returns_entries_and_schema(self):
        text = '@schema x(a: number)\nx(1)\nx(2)\n'
        result = load_raw(io.StringIO(text))
        assert len(result.entries) == 2
        assert result.entries[0] == {"type": "x", "positional": [1], "named": {}}
        assert result.entries[1] == {"type": "x", "positional": [2], "named": {}}
        assert result.schema.has("x")

    def test_load_raw_no_schema(self):
        result = load_raw(io.StringIO('y("hello")\n'))
        assert len(result.entries) == 1
        assert result.entries[0]["type"] == "y"
        assert not result.schema.type_names()


class TestSchemaDuplicateRejection:
    """Schema.from_string/add should reject duplicate type definitions."""

    def test_from_string_duplicate(self):
        with pytest.raises(SchemaError, match="Duplicate"):
            Schema.from_string('@schema x(a: string)\n@schema x(b: number)')

    def test_add_duplicate(self):
        s = Schema.from_string('@schema x(a: string)')
        with pytest.raises(SchemaError, match="Duplicate"):
            s.add('@schema x(b: number)')


class TestIterEntriesFileObject:
    """iter_entries/iter_raw with file objects should produce correct results."""

    def test_file_object_works(self):
        text = '@schema x(a: string)\nx("hello")\n'
        entries = list(iter_entries(io.StringIO(text)))
        assert len(entries) == 1
        assert entries[0] == {"type": "x", "a": "hello"}

    def test_file_object_raw(self):
        entries = list(iter_raw(io.StringIO('x()\ny()\n')))
        assert len(entries) == 2
        assert entries[0]["type"] == 'x'
        assert entries[1]["type"] == 'y'


class TestIgnoreInlineSchema:
    """ignore_inline_schema=True should skip file @schema and not bind entries."""

    def test_loads_ignore_inline_schema(self):
        text = '@schema x(a: string)\nx("hello")\n'
        from fsonl._errors import BindError
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
