"""Python-specific tests — features unique to the Python implementation"""

import io
import pytest
from fsonl import load, load_raw, Schema, RawEntry
from fsonl._errors import ParseError, BindError
from fsonl._types import ParseResult


class TestLoadRaw:
    """load_raw should parse file objects without binding."""

    def test_load_raw_returns_entries_and_schema(self):
        text = '@schema x(a: number)\nx(1)\nx(2)\n'
        result = load_raw(io.StringIO(text))
        assert len(result.entries) == 2
        assert result.entries[0] == RawEntry("x", [1], {})
        assert result.entries[1] == RawEntry("x", [2], {})
        assert result.schema.has("x")

    def test_load_raw_no_schema(self):
        result = load_raw(io.StringIO('y("hello")\n'))
        assert len(result.entries) == 1
        assert result.entries[0].type == "y"
        assert not result.schema.type_names()

    def test_load_raw_returns_raw_entry(self):
        result = load_raw(io.StringIO('z(1, 2)\n'))
        assert isinstance(result.entries[0], RawEntry)


class TestLoad:
    """load(fp) should parse from a file object, binding entries."""

    def test_load_success(self):
        text = '@schema x(a: string)\nx("hello")\n'
        result = load(io.StringIO(text))
        assert len(result) == 1
        assert result[0] == {"type": "x", "a": "hello"}

    def test_load_with_code_schema(self):
        text = 'x("world")\n'
        schema = Schema.from_string('@schema x(a: string)')
        result = load(io.StringIO(text), schema=schema)
        assert result[0] == {"type": "x", "a": "world"}

    def test_load_parse_error(self):
        with pytest.raises(ParseError):
            load(io.StringIO('x(\n'))

    def test_load_bind_error(self):
        text = 'x("hello")\n'
        with pytest.raises(BindError, match="No schema for type"):
            load(io.StringIO(text))

    def test_load_returns_parse_result(self):
        text = '@schema y(n: number)\ny(42)\n'
        result = load(io.StringIO(text))
        assert isinstance(result, ParseResult)
        assert result.schema.has('y')
