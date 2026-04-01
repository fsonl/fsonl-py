"""Common API tests — all language implementations should have equivalent tests.

Covers: error types (ParseError, SchemaError, BindError) — kind field, line field,
str() format as 'line N: message', and that errors raised from loads() carry
correct line numbers.
"""

import pytest
from fsonl import loads, Schema
from fsonl._errors import ParseError, SchemaError, BindError


class TestErrorStrFormat:
    """All 3 error types should format str() as 'line N: message'."""

    def test_parse_error_str_format(self):
        exc = ParseError(3, "some syntax problem")
        assert str(exc) == "line 3: some syntax problem"

    def test_schema_error_str_format(self):
        exc = SchemaError(7, "type mismatch")
        assert str(exc) == "line 7: type mismatch"

    def test_bind_error_str_format(self):
        exc = BindError(12, "no schema")
        assert str(exc) == "line 12: no schema"

    def test_parse_error_kind(self):
        exc = ParseError(1, "msg")
        assert exc.kind == "syntax_error"

    def test_schema_error_kind(self):
        exc = SchemaError(1, "msg")
        assert exc.kind == "schema_error"

    def test_bind_error_kind(self):
        exc = BindError(1, "msg")
        assert exc.kind == "bind_error"

    def test_parse_error_line_attribute(self):
        exc = ParseError(5, "msg")
        assert exc.line == 5

    def test_schema_error_line_attribute(self):
        exc = SchemaError(9, "msg")
        assert exc.line == 9

    def test_bind_error_line_attribute(self):
        exc = BindError(14, "msg")
        assert exc.line == 14

    def test_parse_error_from_loads_has_line(self):
        with pytest.raises(ParseError) as exc_info:
            loads('x(\n')
        assert "line " in str(exc_info.value)

    def test_bind_error_from_loads_has_line(self):
        text = '@schema x(a: string)\nx(42)\n'
        with pytest.raises(BindError) as exc_info:
            loads(text)
        assert "line " in str(exc_info.value)

    def test_schema_error_from_loads_has_line(self):
        code = Schema.from_string('@schema x(a: string)')
        text = '@schema x(a: number)\nx(1)\n'
        with pytest.raises(SchemaError) as exc_info:
            loads(text, schema=code)
        assert "line " in str(exc_info.value)
