"""Common API tests — all language implementations should have equivalent tests.

Covers: Schema.from_string (bare form), Schema.from_file, Schema.from_fsonl,
and the Schema API: has(), get(), type_names() order, get() for missing type.
"""

import os
import tempfile
import pytest
from fsonl import Schema


class TestBareFromString:
    """from_string without @schema prefix."""

    def test_bare_single(self):
        s = Schema.from_string('user(name: string)')
        assert s.has('user')
        assert s.get('user').params[0].name == 'name'

    def test_bare_multiple(self):
        s = Schema.from_string("""
user(name: string, --email: string)
log(level: string, *msg: string[])
""")
        assert s.type_names() == ['user', 'log']

    def test_bare_with_default(self):
        s = Schema.from_string('x(a: string, --b?: number = 42)')
        p = s.get('x').params[1]
        assert p.optional is True
        assert p.has_default is True
        assert p.default == 42

    def test_mixed_prefix_and_bare(self):
        s = Schema.from_string("""
@schema x(a: string)
y(b: number)
""")
        assert s.has('x')
        assert s.has('y')


class TestFromFile:
    """Schema.from_file loads @schema from .fsonl files."""

    def test_from_file(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.fsonl', delete=False) as f:
            f.write('@schema x(a: string)\n@schema y(b: number)\nx("hello")\n')
            f.flush()
            path = f.name
        try:
            s = Schema.from_file(path)
            assert s.type_names() == ['x', 'y']
        finally:
            os.unlink(path)

    def test_from_file_ignores_entries(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.fsonl', delete=False) as f:
            f.write('x("hello")\n@schema x(a: string)\n')
            f.flush()
            path = f.name
        try:
            s = Schema.from_file(path)
            assert s.has('x')
        finally:
            os.unlink(path)


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


class TestSchemaApi:
    """Schema has(), get(), type_names() order preservation, get() for missing type."""

    def test_has_existing_type(self):
        s = Schema.from_string('@schema foo(a: string)')
        assert s.has('foo') is True

    def test_has_missing_type(self):
        s = Schema.from_string('@schema foo(a: string)')
        assert s.has('bar') is False

    def test_has_empty_schema(self):
        s = Schema()
        assert s.has('anything') is False

    def test_get_existing_type(self):
        s = Schema.from_string('@schema foo(a: string)')
        directive = s.get('foo')
        assert directive is not None
        assert directive.name == 'foo'

    def test_get_missing_type_returns_none(self):
        s = Schema.from_string('@schema foo(a: string)')
        assert s.get('bar') is None

    def test_get_empty_schema_returns_none(self):
        s = Schema()
        assert s.get('x') is None

    def test_type_names_order_preserved(self):
        s = Schema.from_string('@schema c(v: number)\n@schema a(v: string)\n@schema b(v: bool)')
        assert s.type_names() == ['c', 'a', 'b']

    def test_type_names_empty_schema(self):
        s = Schema()
        assert s.type_names() == []

    def test_type_names_single(self):
        s = Schema.from_string('@schema x(a: string)')
        assert s.type_names() == ['x']
