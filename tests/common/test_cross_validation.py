"""Common API tests — all language implementations should have equivalent tests.

Covers: cross-validation of inline @schema vs code schema — union order independence,
object field order independence, and variadic type mismatch detection.
"""

import pytest
from fsonl import loads, Schema
from fsonl._errors import SchemaError


class TestUnionOrderIndependence:
    """Union types should match regardless of member order."""

    def test_union_same_order(self):
        code = Schema.from_string('@schema x(a: string | number)')
        text = '@schema x(a: string | number)\nx("hello")\n'
        result = loads(text, schema=code)
        assert result.entries[0] == {"type": "x", "a": "hello"}

    def test_union_reversed_order(self):
        code = Schema.from_string('@schema x(a: string | number)')
        text = '@schema x(a: number | string)\nx("hello")\n'
        result = loads(text, schema=code)
        assert result.entries[0] == {"type": "x", "a": "hello"}

    def test_union_three_types_reordered(self):
        code = Schema.from_string('@schema x(a: string | number | bool)')
        text = '@schema x(a: bool | string | number)\nx(true)\n'
        result = loads(text, schema=code)
        assert result.entries[0] == {"type": "x", "a": True}


class TestObjectFieldOrderIndependence:
    """Object field order should not matter for cross-validation."""

    def test_object_same_order(self):
        code = Schema.from_string('@schema x(a: {x: string, y: number})')
        text = '@schema x(a: {x: string, y: number})\nx({"x": "v", "y": 1})\n'
        result = loads(text, schema=code)
        assert result.entries[0] == {"type": "x", "a": {"x": "v", "y": 1}}

    def test_object_reversed_order(self):
        code = Schema.from_string('@schema x(a: {x: string, y: number})')
        text = '@schema x(a: {y: number, x: string})\nx({"x": "v", "y": 1})\n'
        result = loads(text, schema=code)
        assert result.entries[0] == {"type": "x", "a": {"x": "v", "y": 1}}

    def test_object_three_fields_reordered(self):
        code = Schema.from_string('@schema x(a: {a: string, b: number, c: bool})')
        text = '@schema x(a: {c: bool, a: string, b: number})\nx({"a": "v", "b": 1, "c": true})\n'
        result = loads(text, schema=code)
        assert result.entries[0] == {"type": "x", "a": {"a": "v", "b": 1, "c": True}}


class TestVariadicTypeMismatch:
    """Variadic vs non-variadic triggers type mismatch in cross-validation."""

    def test_variadic_mismatch(self):
        # When variadic differs, types also differ (array vs scalar), so
        # cross-validation raises "type mismatch" before reaching variadic check.
        code = Schema.from_string('@schema x(*a: string[])')
        text = '@schema x(a: string)\nx("hi")\n'
        with pytest.raises(SchemaError):
            loads(text, schema=code)
