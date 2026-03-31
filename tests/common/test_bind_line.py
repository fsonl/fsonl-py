"""Common API tests — all language implementations should have equivalent tests.

Covers: bind() should use the line number from RawEntry for error reporting.
The line information must be internal (not exposed in public interface).
"""

import pytest
from fsonl import loads_raw, bind, Schema
from fsonl._errors import BindError


class TestBindLineFromRawEntry:
    """bind() should report correct line numbers from loads_raw entries."""

    def test_first_line_error(self):
        result = loads_raw("x(42)\n")
        schema = Schema.from_string("@schema x(a: string)")
        with pytest.raises(BindError) as exc_info:
            bind(result.entries[0], schema)
        assert exc_info.value.line == 1

    def test_second_line_error(self):
        result = loads_raw("y(1)\nx(42)\n")
        schema = Schema.from_string("@schema x(a: string)")
        with pytest.raises(BindError) as exc_info:
            bind(result.entries[1], schema)
        assert exc_info.value.line == 2

    def test_multi_entry_each_line(self):
        result = loads_raw("a(1)\nb(2)\nc(3)\n")
        schema = Schema.from_string("@schema c(x: string)")
        with pytest.raises(BindError) as exc_info:
            bind(result.entries[2], schema)
        assert exc_info.value.line == 3

    def test_with_schema_lines_offset(self):
        text = "@schema x(a: string)\nx(42)\n"
        result = loads_raw(text)
        schema = Schema.from_string("@schema x(a: string)")
        with pytest.raises(BindError) as exc_info:
            bind(result.entries[0], schema)
        assert exc_info.value.line == 2

    def test_no_schema_error_has_line(self):
        result = loads_raw("unknown(1)\n")
        schema = Schema()
        with pytest.raises(BindError) as exc_info:
            bind(result.entries[0], schema)
        assert exc_info.value.line == 1


class TestRawEntryLineNotExposed:
    """Line information must not be visible in RawEntry's public interface."""

    def test_line_not_in_keys(self):
        result = loads_raw("x(1)\n")
        entry = result.entries[0]
        keys = entry.keys()
        assert "line" not in keys
        assert "_line" not in keys

    def test_line_not_in_to_dict(self):
        result = loads_raw("x(1)\n")
        entry = result.entries[0]
        d = entry.to_dict()
        assert "line" not in d
        assert "_line" not in d

    def test_line_not_in_items(self):
        result = loads_raw("x(1)\n")
        entry = result.entries[0]
        item_keys = [k for k, v in entry.items()]
        assert "line" not in item_keys
        assert "_line" not in item_keys
