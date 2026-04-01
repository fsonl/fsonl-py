"""Common API tests — all language implementations should have equivalent tests.

Covers: variadic parameter serialization — array expansion as positional args,
empty arrays, non-list errors, and positional+variadic combinations.
"""

import pytest
from fsonl import dumps, loads, Schema


class TestVariadicBasic:
    """Variadic params expand array elements as individual positional args."""

    def test_single_element(self):
        s = Schema.from_string('@schema x(*msg: string[])')
        result = dumps([{"type": "x", "msg": ["hello"]}], schema=s, exclude_schema=True)
        assert result == 'x("hello")\n'

    def test_multiple_elements(self):
        s = Schema.from_string('@schema x(*msg: string[])')
        result = dumps([{"type": "x", "msg": ["a", "b", "c"]}], schema=s, exclude_schema=True)
        assert result == 'x("a", "b", "c")\n'

    def test_empty_array(self):
        s = Schema.from_string('@schema x(*msg: string[])')
        result = dumps([{"type": "x", "msg": []}], schema=s, exclude_schema=True)
        assert result == 'x()\n'

    def test_number_variadic(self):
        s = Schema.from_string('@schema x(*vals: number[])')
        result = dumps([{"type": "x", "vals": [1, 2, 3]}], schema=s, exclude_schema=True)
        assert result == 'x(1, 2, 3)\n'


class TestVariadicErrors:
    """Variadic params must receive a list value."""

    def test_string_not_list(self):
        s = Schema.from_string('@schema x(*msg: string[])')
        with pytest.raises((TypeError, ValueError)):
            dumps([{"type": "x", "msg": "not-a-list"}], schema=s)

    def test_number_not_list(self):
        s = Schema.from_string('@schema x(*msg: string[])')
        with pytest.raises((TypeError, ValueError)):
            dumps([{"type": "x", "msg": 42}], schema=s)

    def test_none_not_list(self):
        s = Schema.from_string('@schema x(*msg: string[])')
        with pytest.raises((TypeError, ValueError)):
            dumps([{"type": "x", "msg": None}], schema=s)


class TestVariadicWithPositional:
    """Positional params followed by variadic."""

    def test_positional_then_variadic(self):
        s = Schema.from_string('@schema x(level: string, *msg: string[])')
        result = dumps(
            [{"type": "x", "level": "info", "msg": ["a", "b"]}],
            schema=s, exclude_schema=True,
        )
        assert result == 'x("info", "a", "b")\n'

    def test_positional_then_empty_variadic(self):
        s = Schema.from_string('@schema x(level: string, *msg: string[])')
        result = dumps(
            [{"type": "x", "level": "info", "msg": []}],
            schema=s, exclude_schema=True,
        )
        assert result == 'x("info")\n'

    def test_positional_variadic_roundtrip(self):
        s = Schema.from_string('@schema x(level: string, *msg: string[])')
        entry = {"type": "x", "level": "info", "msg": ["a", "b"]}
        text = dumps([entry], schema=s, exclude_schema=True)
        result = loads(text, schema=s)
        assert result.entries[0] == entry


class TestVariadicWithNamed:
    """Named params combined with variadic."""

    def test_positional_variadic_named(self):
        """positional → variadic → named order is valid in schema."""
        s = Schema.from_string('@schema x(level: string, *msg: string[], --tag: string)')
        result = dumps(
            [{"type": "x", "level": "info", "msg": ["a", "b"], "tag": "t"}],
            schema=s, exclude_schema=True,
        )
        assert result == 'x("info", "a", "b", tag="t")\n'
