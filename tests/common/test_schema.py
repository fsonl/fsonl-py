"""Common API tests — all language implementations should have equivalent tests.

Covers: Schema.from_string (bare form),
and the Schema API: has(), get(), type_names() order, get() for missing type.
"""

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
