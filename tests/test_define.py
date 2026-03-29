"""Tests for Schema.define decorator, OMIT sentinel, from_file, bare from_string."""

import os
import sys
import tempfile
import pytest
from fsonl import Schema, dumps, loads, OMIT


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
            # entries are ignored, only @schema extracted
            s = Schema.from_file(path)
            assert s.has('x')
        finally:
            os.unlink(path)


class TestOMIT:
    """OMIT sentinel for optional-without-default."""

    def test_omit_repr(self):
        assert repr(OMIT) == "OMIT"

    def test_omit_is_truthy(self):
        assert OMIT

    def test_omit_is_singleton(self):
        from fsonl._types import _OmitType
        assert OMIT is _OmitType()


@pytest.mark.skipif(sys.version_info < (3, 10), reason="requires 3.10+")
class TestDefineDecorator:
    """Schema.define decorator."""

    def test_basic_positional_and_named(self):
        s = Schema()

        @s.define
        def user(name: str, *, email: str): ...

        assert s.has('user')
        params = s.get('user').params
        assert params[0].name == 'name'
        assert params[0].kind == 'positional'
        assert params[0].schema_type == 'string'
        assert params[1].name == 'email'
        assert params[1].kind == 'named'

    def test_named_with_default(self):
        s = Schema()

        @s.define
        def x(a: str, *, b: int = 10): ...

        p = s.get('x').params[1]
        assert p.optional is True
        assert p.has_default is True
        assert p.default == 10

    def test_omit_optional_no_default(self):
        s = Schema()

        @s.define
        def x(a: str, *, b: str = OMIT): ...

        p = s.get('x').params[1]
        assert p.optional is True
        assert p.has_default is False
        assert p.default is None

    def test_variadic(self):
        s = Schema()

        @s.define
        def log(level: str, *msg: str): ...

        p = s.get('log').params[1]
        assert p.variadic is True
        assert p.schema_type == {"kind": "array", "element": "string"}

    def test_type_mapping(self):
        s = Schema()

        @s.define
        def x(a: str, b: int, c: float, d: bool): ...

        types = [p.schema_type for p in s.get('x').params]
        assert types == ['string', 'number', 'number', 'bool']

    def test_list_type(self):
        s = Schema()

        @s.define
        def x(*, tags: list[str] = OMIT): ...

        p = s.get('x').params[0]
        assert p.schema_type == {"kind": "array", "element": "string"}

    def test_union_type(self):
        s = Schema()

        @s.define
        def x(*, val: str | None = None): ...

        p = s.get('x').params[0]
        assert p.schema_type == {"kind": "union", "types": ["string", "null"]}

    def test_round_trip(self):
        s = Schema()

        @s.define
        def user(name: str, *, email: str, role: str = "member"): ...

        entry = {"type": "user", "name": "alice", "email": "a@b.com", "role": "admin"}
        text = dumps(entry, schema=s, exclude_schema=True)
        result = loads(text, schema=s)
        assert result.entries[0] == entry

    def test_missing_annotation_raises(self):
        s = Schema()
        with pytest.raises(TypeError, match="must have a type annotation"):
            @s.define
            def x(a): ...

    def test_returns_original_function(self):
        s = Schema()

        @s.define
        def my_func(a: str): ...

        assert my_func.__name__ == 'my_func'
