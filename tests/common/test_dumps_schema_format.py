"""Common API tests — all language implementations should have equivalent tests.

Covers: dumps() @schema directive output for all type combinations.
Verifies that dumps → loads round-trip preserves schema structure.
"""

import pytest
from fsonl import dumps, loads, Schema


class TestSchemaFormatPrimitive:
    """@schema output for primitive types."""

    def test_string(self):
        s = Schema.from_string('@schema x(a: string)')
        out = dumps({"type": "x", "a": "v"}, schema=s)
        assert out.startswith('@schema x(a: string)\n')

    def test_number(self):
        s = Schema.from_string('@schema x(a: number)')
        out = dumps({"type": "x", "a": 1}, schema=s)
        assert out.startswith('@schema x(a: number)\n')

    def test_bool(self):
        s = Schema.from_string('@schema x(a: bool)')
        out = dumps({"type": "x", "a": True}, schema=s)
        assert out.startswith('@schema x(a: bool)\n')

    def test_null(self):
        s = Schema.from_string('@schema x(a: null)')
        out = dumps({"type": "x", "a": None}, schema=s)
        assert out.startswith('@schema x(a: null)\n')

    def test_any(self):
        s = Schema.from_string('@schema x(a: any)')
        out = dumps({"type": "x", "a": "v"}, schema=s)
        assert out.startswith('@schema x(a: any)\n')


class TestSchemaFormatArray:
    """@schema output for array types."""

    def test_simple_array(self):
        s = Schema.from_string('@schema x(a: string[])')
        out = dumps({"type": "x", "a": ["v"]}, schema=s)
        assert out.startswith('@schema x(a: string[])\n')

    def test_nested_array(self):
        s = Schema.from_string('@schema x(a: string[][])')
        out = dumps({"type": "x", "a": [["v"]]}, schema=s)
        assert out.startswith('@schema x(a: string[][])\n')

    def test_union_in_array(self):
        s = Schema.from_string('@schema x(a: (string | number)[])')
        out = dumps({"type": "x", "a": ["v"]}, schema=s)
        assert out.startswith('@schema x(a: (string | number)[])\n')


class TestSchemaFormatUnion:
    """@schema output for union types."""

    def test_two_types(self):
        s = Schema.from_string('@schema x(a: string | number)')
        out = dumps({"type": "x", "a": "v"}, schema=s)
        assert out.startswith('@schema x(a: string | number)\n')

    def test_three_types(self):
        s = Schema.from_string('@schema x(a: string | number | null)')
        out = dumps({"type": "x", "a": "v"}, schema=s)
        assert out.startswith('@schema x(a: string | number | null)\n')


class TestSchemaFormatObject:
    """@schema output for object types."""

    def test_simple_object(self):
        s = Schema.from_string('@schema x(a: { k: string })')
        out = dumps({"type": "x", "a": {"k": "v"}}, schema=s)
        assert out.startswith('@schema x(a: { k: string })\n')

    def test_object_with_optional(self):
        s = Schema.from_string('@schema x(a: { k: string, v?: number })')
        out = dumps({"type": "x", "a": {"k": "v"}}, schema=s)
        assert out.startswith('@schema x(a: { k: string, v?: number })\n')

    def test_nested_object(self):
        s = Schema.from_string('@schema x(a: { inner: { val: string } })')
        out = dumps({"type": "x", "a": {"inner": {"val": "v"}}}, schema=s)
        assert out.startswith('@schema x(a: { inner: { val: string } })\n')


class TestSchemaFormatParams:
    """@schema output for various parameter kinds."""

    def test_positional(self):
        s = Schema.from_string('@schema x(a: string)')
        out = dumps({"type": "x", "a": "v"}, schema=s)
        assert '@schema x(a: string)' in out

    def test_named(self):
        s = Schema.from_string('@schema x(--a: string)')
        out = dumps({"type": "x", "a": "v"}, schema=s)
        assert '@schema x(--a: string)' in out

    def test_optional_without_default(self):
        s = Schema.from_string('@schema x(--a?: string)')
        out = dumps({"type": "x"}, schema=s)
        assert '@schema x(--a?: string)' in out

    def test_with_default_number(self):
        s = Schema.from_string('@schema x(--a: number = 42)')
        out = dumps({"type": "x"}, schema=s)
        assert '@schema x(--a: number = 42)' in out

    def test_with_default_string(self):
        s = Schema.from_string('@schema x(--a: string = "hello")')
        out = dumps({"type": "x"}, schema=s)
        assert '@schema x(--a: string = "hello")' in out

    def test_with_default_bool(self):
        s = Schema.from_string('@schema x(--a: bool = false)')
        out = dumps({"type": "x"}, schema=s)
        assert '@schema x(--a: bool = false)' in out

    def test_with_default_null(self):
        s = Schema.from_string('@schema x(--a: string | null = null)')
        out = dumps({"type": "x"}, schema=s)
        assert '@schema x(--a: string | null = null)' in out

    def test_with_default_array(self):
        s = Schema.from_string('@schema x(--a: string[] = [])')
        out = dumps({"type": "x"}, schema=s)
        assert '@schema x(--a: string[] = [])' in out

    def test_variadic(self):
        s = Schema.from_string('@schema x(*a: string[])')
        out = dumps({"type": "x", "a": ["v"]}, schema=s)
        assert '@schema x(*a: string[])' in out


class TestSchemaFormatMultiParam:
    """@schema with multiple parameters of mixed kinds."""

    def test_positional_and_named(self):
        s = Schema.from_string('@schema x(a: string, --b: number)')
        out = dumps({"type": "x", "a": "v", "b": 1}, schema=s)
        assert '@schema x(a: string, --b: number)' in out

    def test_positional_named_optional_default(self):
        s = Schema.from_string('@schema x(a: string, --b?: number, --c: bool = true)')
        out = dumps({"type": "x", "a": "v"}, schema=s)
        assert '@schema x(a: string, --b?: number, --c: bool = true)' in out

    def test_positional_and_variadic(self):
        s = Schema.from_string('@schema x(level: string, *msg: string[])')
        out = dumps({"type": "x", "level": "info", "msg": ["a", "b"]}, schema=s)
        assert '@schema x(level: string, *msg: string[])' in out


class TestSchemaFormatRoundTrip:
    """dumps @schema output should be parseable back by loads."""

    def test_complex_schema_roundtrip(self):
        schema_text = '@schema evt(name: string, --data?: { key: string, val?: number }, --tags: string[] = [])'
        s = Schema.from_string(schema_text)
        entry = {"type": "evt", "name": "click", "tags": ["ui"]}
        text = dumps(entry, schema=s)
        result = loads(text, schema=s)
        assert result.entries[0]["name"] == "click"
        assert result.entries[0]["tags"] == ["ui"]

    def test_multi_type_schema_roundtrip(self):
        s = Schema.from_string('@schema a(x: string)\n@schema b(y: number)')
        entries = [{"type": "a", "x": "v"}, {"type": "b", "y": 1}]
        text = dumps(entries, schema=s)
        result = loads(text, schema=s)
        assert result.entries[0] == {"type": "a", "x": "v"}
        assert result.entries[1] == {"type": "b", "y": 1}

    def test_union_array_schema_roundtrip(self):
        s = Schema.from_string('@schema x(a: (string | number)[])')
        entry = {"type": "x", "a": ["hello", 42]}
        text = dumps(entry, schema=s)
        result = loads(text, schema=s)
        assert result.entries[0] == entry

    def test_exclude_schema_no_directive(self):
        s = Schema.from_string('@schema x(a: string)')
        text = dumps({"type": "x", "a": "v"}, schema=s, exclude_schema=True)
        assert '@schema' not in text
        assert text == 'x("v")\n'
