"""Common API tests — all language implementations should have equivalent tests.

Covers: bind() no-schema error, mutable default deep copy, basic bind,
extra field policies, and line number propagation.
"""

import pytest
from fsonl import bind, loads, Schema, RawEntry
from fsonl._errors import BindError


class TestBindNoSchema:
    """bind() with missing schema should raise BindError, not SchemaError."""

    def test_no_schema_for_type(self):
        entry = RawEntry("unknown", [], {})
        schema = Schema()
        with pytest.raises(BindError, match="No schema for type 'unknown'"):
            bind(entry, schema)

    def test_error_preserves_line(self):
        entry = RawEntry("missing", [], {})
        schema = Schema()
        with pytest.raises(BindError) as exc_info:
            bind(entry, schema, line=42)
        assert exc_info.value.line == 42
        assert exc_info.value.kind == "bind_error"


class TestMutableDefaultDeepCopy:
    """Schema with list/dict default should produce independent copies per bind."""

    def test_list_default_not_shared(self):
        schema = Schema.from_string('@schema x(--tags: string[] = [])')
        text = 'x()\nx()\n'
        result = loads(text, schema=schema)
        entry_a = result[0]
        entry_b = result[1]
        assert entry_a["tags"] == []
        assert entry_b["tags"] == []
        entry_a["tags"].append("foo")
        assert entry_b["tags"] == []

    def test_dict_default_not_shared(self):
        schema = Schema.from_string('@schema x(--meta: {k: string} = {"k": "v"})')
        text = 'x()\nx()\n'
        result = loads(text, schema=schema)
        entry_a = result[0]
        entry_b = result[1]
        entry_a["meta"]["k"] = "changed"
        assert entry_b["meta"]["k"] == "v"


class TestBindBasic:
    """bind() with normal positional + named params."""

    def test_positional_param(self):
        schema = Schema.from_string('@schema x(a: string)')
        entry = RawEntry("x", ["hello"], {})
        result = bind(entry, schema)
        assert result["a"] == "hello"
        assert result["type"] == "x"

    def test_named_param(self):
        schema = Schema.from_string('@schema x(--b: number)')
        entry = RawEntry("x", [], {"b": 42})
        result = bind(entry, schema)
        assert result["b"] == 42

    def test_positional_and_named(self):
        schema = Schema.from_string('@schema x(a: string, --b: number)')
        entry = RawEntry("x", ["hi"], {"b": 7})
        result = bind(entry, schema)
        assert result["a"] == "hi"
        assert result["b"] == 7

    def test_optional_named_absent(self):
        schema = Schema.from_string('@schema x(a: string, --b?: number)')
        entry = RawEntry("x", ["ok"], {})
        result = bind(entry, schema)
        assert result["a"] == "ok"
        assert "b" not in result

    def test_named_with_default_absent(self):
        schema = Schema.from_string('@schema x(a: string, --b: number = 99)')
        entry = RawEntry("x", ["ok"], {})
        result = bind(entry, schema)
        assert result["b"] == 99


class TestBindExtraFields:
    """bind() respects extra field policies."""

    def test_extra_field_raises_by_default(self):
        schema = Schema.from_string('@schema x(a: string)')
        text = 'x("ok")\n'
        # loads with extra positional to produce an entry with extras
        # Test via loads with explicit extra_fields error policy
        from fsonl._types import ExtraFieldPolicy
        with pytest.raises(BindError):
            loads(
                '@schema x(a: string)\nx("ok", b=2)\n',
                schema=Schema.from_string('@schema x(a: string)'),
                extra_fields=ExtraFieldPolicy.ERROR,
            )

    def test_extra_field_strip(self):
        from fsonl._types import ExtraFieldPolicy
        schema = Schema.from_string('@schema x(a: string)')
        result = loads(
            '@schema x(a: string)\nx("ok", b=2)\n',
            schema=schema,
            extra_fields=ExtraFieldPolicy.STRIP,
        )
        assert result[0]["a"] == "ok"
        assert "b" not in result[0]

    def test_extra_field_preserve(self):
        from fsonl._types import ExtraFieldPolicy
        schema = Schema.from_string('@schema x(a: string)')
        result = loads(
            '@schema x(a: string)\nx("ok", b=2)\n',
            schema=schema,
            extra_fields=ExtraFieldPolicy.PRESERVE,
        )
        assert result[0]["a"] == "ok"
        assert result[0]["b"] == 2


class TestBindLineNumber:
    """bind() line number is passed through to BindError."""

    def test_line_number_in_error(self):
        schema = Schema.from_string('@schema x(a: string)')
        entry = RawEntry("x", [42], {})
        with pytest.raises(BindError) as exc_info:
            bind(entry, schema, line=5)
        assert exc_info.value.line == 5

    def test_line_number_str_format(self):
        schema = Schema.from_string('@schema x(a: string)')
        entry = RawEntry("x", [42], {})
        with pytest.raises(BindError) as exc_info:
            bind(entry, schema, line=3)
        assert "line 3" in str(exc_info.value)
