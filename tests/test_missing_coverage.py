"""Tests for all 16 missing coverage items identified in TEST_REVIEW_RESULT.md."""

import io
import copy
import tempfile
import os
import pytest

from fsonl import loads, loads_raw, load, dump, dumps, Schema
from fsonl._errors import ParseError, SchemaError, BindError
from fsonl._types import (
    ParseResult, ExtraFieldPolicy, SchemaParam, SchemaDirective
)


# ── Item 1: load(fp) — success and error paths ──────────────────────────────

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


# ── Item 2: dump(entries, fp) — file output, with schema, with exclude_schema ─

class TestDump:
    """dump() should write serialized FSONL to a file object."""

    def test_dump_single_entry(self):
        buf = io.StringIO()
        dump({"type": "x", "v": 1}, buf)
        assert buf.getvalue() == 'x(v=1)\n'

    def test_dump_with_schema(self):
        schema = Schema.from_string('@schema x(a: string)')
        buf = io.StringIO()
        dump({"type": "x", "a": "hi"}, buf, schema=schema)
        assert buf.getvalue() == '@schema x(a: string)\nx("hi")\n'

    def test_dump_with_exclude_schema(self):
        schema = Schema.from_string('@schema x(a: string)')
        buf = io.StringIO()
        dump({"type": "x", "a": "hi"}, buf, schema=schema, exclude_schema=True)
        assert buf.getvalue() == 'x("hi")\n'

    def test_dump_list_of_entries(self):
        schema = Schema.from_string('@schema x(a: string)')
        buf = io.StringIO()
        entries = [{"type": "x", "a": "one"}, {"type": "x", "a": "two"}]
        dump(entries, buf, schema=schema, exclude_schema=True)
        assert buf.getvalue() == 'x("one")\nx("two")\n'

    def test_dump_writes_to_real_file(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.fsonl', delete=False) as f:
            path = f.name
            dump({"type": "ev", "n": 7}, f)
        try:
            with open(path) as f:
                assert f.read() == 'ev(n=7)\n'
        finally:
            os.unlink(path)


# ── Item 3: ParseError — directly trigger via malformed FSONL ─────────────────

class TestParseError:
    """ParseError should be raised for syntax errors in FSONL input."""

    def test_unclosed_paren(self):
        with pytest.raises(ParseError):
            loads('x(\n')

    def test_positional_after_named(self):
        with pytest.raises(ParseError, match="Positional argument after named argument"):
            loads_raw('x(a=1, 2)\n')

    def test_trailing_comma(self):
        with pytest.raises(ParseError, match="Trailing comma"):
            loads_raw('x(1,)\n')

    def test_incomplete_schema_directive(self):
        with pytest.raises(ParseError, match="Incomplete @schema directive"):
            loads_raw('@schema\n')

    def test_unexpected_content_after_paren(self):
        with pytest.raises(ParseError, match="Unexpected content after"):
            loads_raw('x() garbage\n')

    def test_reserved_type_key_in_args(self):
        with pytest.raises(ParseError, match="'type' is reserved"):
            loads_raw('x(type=1)\n')


# ── Item 4: ExtraFieldPolicy.PRESERVE and STRIP on binder side ───────────────

class TestExtraFieldPolicy:
    """ExtraFieldPolicy.PRESERVE and STRIP should handle undeclared named args."""

    def setup_method(self):
        self.schema = Schema.from_string('@schema x(a: string)')

    def test_preserve_keeps_extra_fields(self):
        text = 'x("hello", extra=42)\n'
        result = loads(text, schema=self.schema, extra_fields=ExtraFieldPolicy.PRESERVE)
        assert result[0] == {"type": "x", "a": "hello", "extra": 42}

    def test_strip_removes_extra_fields(self):
        text = 'x("hello", extra=42)\n'
        result = loads(text, schema=self.schema, extra_fields=ExtraFieldPolicy.STRIP)
        assert result[0] == {"type": "x", "a": "hello"}
        assert "extra" not in result[0]

    def test_error_policy_raises_on_extra(self):
        text = 'x("hello", extra=42)\n'
        with pytest.raises(BindError, match="Undeclared named argument"):
            loads(text, schema=self.schema, extra_fields=ExtraFieldPolicy.ERROR)

    def test_preserve_multiple_extra_fields(self):
        text = 'x("hello", p=1, q=2)\n'
        result = loads(text, schema=self.schema, extra_fields=ExtraFieldPolicy.PRESERVE)
        assert result[0]["p"] == 1
        assert result[0]["q"] == 2

    def test_strip_with_no_extras_is_same(self):
        text = 'x("hello")\n'
        result = loads(text, schema=self.schema, extra_fields=ExtraFieldPolicy.STRIP)
        assert result[0] == {"type": "x", "a": "hello"}


# ── Item 5: Error str(exc) contains "line N:" for all 3 error types ──────────

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


# ── Item 6: Empty input loads('') returns empty entries ──────────────────────

class TestEmptyInput:
    """Empty input should return empty ParseResult with no entries."""

    def test_loads_empty_string(self):
        result = loads('')
        assert result.entries == []

    def test_loads_empty_returns_parse_result(self):
        result = loads('')
        assert isinstance(result, ParseResult)

    def test_loads_raw_empty_string(self):
        result = loads_raw('')
        assert result.entries == []

    def test_loads_whitespace_only(self):
        result = loads('   \n   \n')
        assert result.entries == []


# ── Item 7: BOM handling ──────────────────────────────────────────────────────

class TestBOMHandling:
    """BOM at start of input should be silently stripped."""

    def test_loads_raw_with_bom(self):
        result = loads_raw('\uFEFFx()\n')
        assert len(result.entries) == 1
        assert result.entries[0]["type"] == 'x'

    def test_loads_with_bom_and_schema(self):
        text = '\uFEFF@schema x(a: number)\nx(1)\n'
        result = loads(text)
        assert result.entries[0] == {"type": "x", "a": 1}

    def test_bom_only_input(self):
        result = loads_raw('\uFEFF')
        assert result.entries == []


# ── Item 8: CRLF and bare \r handling ────────────────────────────────────────

class TestLineEndings:
    """CRLF should work; bare \\r should raise ParseError."""

    def test_crlf_returns_two_entries(self):
        result = loads_raw('x()\r\ny()\r\n')
        assert len(result.entries) == 2
        assert result.entries[0]["type"] == 'x'
        assert result.entries[1]["type"] == 'y'

    def test_bare_cr_raises_parse_error(self):
        with pytest.raises(ParseError):
            loads_raw('x()\ry()\n')

    def test_crlf_with_schema(self):
        text = '@schema x(a: number)\r\nx(1)\r\n'
        result = loads(text)
        assert result.entries[0] == {"type": "x", "a": 1}


# ── Item 9: Schema.from_fsonl() — extracts schemas, ignores non-schema lines ─

class TestSchemaFromFsonl:
    """Schema.from_fsonl() should extract @schema lines and ignore entries."""

    def test_extracts_schema_lines(self):
        text = '@schema x(a: string)\n@schema y(b: number)\nx("hello")\n'
        schema = Schema.from_fsonl(text)
        assert schema.has('x')
        assert schema.has('y')

    def test_ignores_entry_lines(self):
        text = 'x("hello")\n@schema x(a: string)\ny(42)\n'
        schema = Schema.from_fsonl(text)
        assert schema.has('x')
        assert not schema.has('y')

    def test_ignores_comment_lines(self):
        text = '// a comment\n@schema z(n: number)\n// another\n'
        schema = Schema.from_fsonl(text)
        assert schema.has('z')
        assert schema.type_names() == ['z']

    def test_ignores_blank_lines(self):
        text = '\n@schema a(v: bool)\n\n'
        schema = Schema.from_fsonl(text)
        assert schema.has('a')

    def test_empty_fsonl_returns_empty_schema(self):
        schema = Schema.from_fsonl('')
        assert schema.type_names() == []


# ── Item 10: `any` type via text schema ──────────────────────────────────────

class TestAnyType:
    """Schema with 'any' type should accept any value."""

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

    def test_any_accepts_bool(self):
        schema = Schema.from_string('@schema x(a: any)')
        text = 'x(true)\n'
        result = loads(text, schema=schema)
        assert result[0]["a"] is True

    def test_any_accepts_null(self):
        schema = Schema.from_string('@schema x(a: any)')
        text = 'x(null)\n'
        result = loads(text, schema=schema)
        assert result[0]["a"] is None

    def test_any_accepts_array(self):
        schema = Schema.from_string('@schema x(a: any)')
        text = 'x([1, 2, 3])\n'
        result = loads(text, schema=schema)
        assert result[0]["a"] == [1, 2, 3]


# ── Item 11: _cross_validate remaining branches ───────────────────────────────

class TestCrossValidateBranches:
    """_cross_validate should catch param count, name, kind, optional, variadic, default mismatches."""

    def test_param_count_mismatch(self):
        code = Schema.from_string('@schema x(a: string, b: number)')
        text = '@schema x(a: string)\nx("hi")\n'
        with pytest.raises(SchemaError, match="Parameter count mismatch"):
            loads(text, schema=code)

    def test_name_mismatch(self):
        code = Schema.from_string('@schema x(a: string)')
        text = '@schema x(b: string)\nx("hi")\n'
        with pytest.raises(SchemaError, match="name mismatch"):
            loads(text, schema=code)

    def test_kind_mismatch(self):
        # code has named (--a), file has positional (a)
        code = Schema.from_string('@schema x(--a: string)')
        text = '@schema x(a: string)\nx("hi")\n'
        with pytest.raises(SchemaError, match="kind mismatch"):
            loads(text, schema=code)

    def test_optional_mismatch(self):
        code = Schema.from_string('@schema x(--a?: string)')
        text = '@schema x(--a: string)\nx(a="hi")\n'
        with pytest.raises(SchemaError, match="optional mismatch"):
            loads(text, schema=code)

    def test_variadic_mismatch(self):
        # When variadic differs, types also differ (array vs scalar), so
        # _cross_validate raises "type mismatch" before reaching variadic check.
        # Test that the cross-validation does reject this combination.
        code = Schema.from_string('@schema x(*a: string[])')
        text = '@schema x(a: string)\nx("hi")\n'
        with pytest.raises(SchemaError):
            loads(text, schema=code)

    def test_default_value_mismatch(self):
        code = Schema.from_string('@schema x(--a: number = 10)')
        text = '@schema x(--a: number = 99)\nx()\n'
        with pytest.raises(SchemaError, match="default value mismatch"):
            loads(text, schema=code)


# ── Item 12: dumps with list input ───────────────────────────────────────────

class TestDumpsList:
    """dumps() with a list of entries should serialize all of them."""

    def test_dumps_empty_list(self):
        assert dumps([]) == ''

    def test_dumps_single_item_list(self):
        assert dumps([{"type": "x", "v": 1}]) == 'x(v=1)\n'

    def test_dumps_multiple_entries(self):
        entries = [{"type": "a", "n": 1}, {"type": "b", "n": 2}]
        result = dumps(entries)
        assert result == 'a(n=1)\nb(n=2)\n'

    def test_dumps_list_with_schema(self):
        schema = Schema.from_string('@schema x(a: string)')
        entries = [{"type": "x", "a": "one"}, {"type": "x", "a": "two"}]
        result = dumps(entries, schema=schema, exclude_schema=True)
        assert result == 'x("one")\nx("two")\n'

    def test_dumps_list_with_schema_prepends_once(self):
        schema = Schema.from_string('@schema x(a: string)')
        entries = [{"type": "x", "a": "one"}, {"type": "x", "a": "two"}]
        result = dumps(entries, schema=schema)
        assert result.count('@schema') == 1
        assert result.startswith('@schema x(a: string)\n')


# ── Item 13: ParseResult protocol ────────────────────────────────────────────

class TestParseResultProtocol:
    """ParseResult should support __iter__, __len__, __getitem__."""

    def setup_method(self):
        self.result = loads_raw('a()\nb()\nc()\n')

    def test_len(self):
        assert len(self.result) == 3

    def test_getitem(self):
        assert self.result[0]["type"] == 'a'
        assert self.result[1]["type"] == 'b'
        assert self.result[2]["type"] == 'c'

    def test_iter(self):
        types = [e["type"] for e in self.result]
        assert types == ['a', 'b', 'c']

    def test_iter_is_idempotent(self):
        first = list(self.result)
        second = list(self.result)
        assert first == second

    def test_negative_index(self):
        assert self.result[-1]["type"] == 'c'


# ── Item 14: SchemaParam.to_dict() and SchemaDirective.to_dict() ──────────────

class TestToDict:
    """SchemaParam and SchemaDirective to_dict() should return correct structures."""

    def test_schema_param_to_dict(self):
        param = SchemaParam(
            name="foo",
            kind="positional",
            schema_type="string",
            optional=False,
            variadic=False,
            has_default=False,
            default=None,
        )
        d = param.to_dict()
        assert d["name"] == "foo"
        assert d["kind"] == "positional"
        assert d["type"] == "string"
        assert d["optional"] is False
        assert d["variadic"] is False
        assert d["has_default"] is False
        assert d["default"] is None

    def test_schema_param_to_dict_with_default(self):
        param = SchemaParam(
            name="n",
            kind="named",
            schema_type="number",
            optional=True,
            variadic=False,
            has_default=True,
            default=42,
        )
        d = param.to_dict()
        assert d["optional"] is True
        assert d["has_default"] is True
        assert d["default"] == 42

    def test_schema_param_array_type_to_dict(self):
        param = SchemaParam(
            name="tags",
            kind="positional",
            schema_type={"kind": "array", "element": "string"},
        )
        d = param.to_dict()
        assert d["type"] == {"array": "string"}

    def test_schema_directive_to_dict(self):
        param = SchemaParam(name="a", kind="positional", schema_type="string")
        directive = SchemaDirective(name="x", params=[param], line=1)
        d = directive.to_dict()
        assert d["@schema"] == "x"
        assert len(d["params"]) == 1
        assert d["params"][0]["name"] == "a"

    def test_schema_directive_to_dict_no_params(self):
        directive = SchemaDirective(name="evt", params=[], line=5)
        d = directive.to_dict()
        assert d["@schema"] == "evt"
        assert d["params"] == []

    def test_round_trip_to_dict_via_schema(self):
        schema = Schema.from_string('@schema x(a: string, --b: number)')
        directive = schema.get('x')
        d = directive.to_dict()
        assert d["@schema"] == "x"
        assert d["params"][0]["name"] == "a"
        assert d["params"][1]["name"] == "b"


# ── Item 15: Mutable default deepcopy ────────────────────────────────────────

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
        # Mutate one; the other should be unaffected
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


# ── Item 16: Comments-only input ─────────────────────────────────────────────

class TestCommentsOnlyInput:
    """Input with only comments should return empty entries."""

    def test_single_comment_line(self):
        result = loads('// comment\n')
        assert result.entries == []

    def test_multiple_comment_lines(self):
        result = loads('// first\n// second\n// third\n')
        assert result.entries == []

    def test_loads_raw_comment_only(self):
        result = loads_raw('// comment\n')
        assert result.entries == []

    def test_comments_mixed_with_blank_lines(self):
        result = loads('\n// comment\n\n')
        assert result.entries == []

    def test_comments_do_not_interfere_with_entries(self):
        text = '// header\n@schema x(a: number)\n// mid\nx(1)\n// footer\n'
        result = loads(text)
        assert len(result.entries) == 1
        assert result[0]["a"] == 1
