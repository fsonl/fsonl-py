"""Python-specific tests — features unique to the Python implementation"""

import sys
import pytest
from fsonl import Schema, dumps, loads, OMIT, ParamKind


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
        assert params[0].kind == ParamKind.POSITIONAL
        assert params[0].schema_type == 'string'
        assert params[1].name == 'email'
        assert params[1].kind == ParamKind.NAMED

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
        text = dumps([entry], schema=s, exclude_schema=True)
        result = loads(text, schema=s)
        assert result.entries[0] == entry

    def test_dict_maps_to_any(self):
        s = Schema()

        @s.define
        def x(a: str, *, meta: dict): ...

        p_pos = s.get('x').params[0]
        assert p_pos.schema_type == 'string'
        p_named = s.get('x').params[1]
        assert p_named.schema_type == 'any'

    def test_any_maps_to_any(self):
        from typing import Any
        s = Schema()

        @s.define
        def x(payload: Any): ...

        p = s.get('x').params[0]
        assert p.schema_type == 'any'

    def test_dict_positional(self):
        s = Schema()

        @s.define
        def x(data: dict): ...

        p = s.get('x').params[0]
        assert p.schema_type == 'any'
        assert p.kind == ParamKind.POSITIONAL

    def test_dict_str_any_maps_to_any(self):
        from typing import Any
        s = Schema()

        @s.define
        def x(*, meta: dict[str, Any]): ...

        p = s.get('x').params[0]
        assert p.schema_type == 'any'

    def test_dict_str_int_maps_to_any(self):
        s = Schema()

        @s.define
        def x(*, counts: dict[str, int]): ...

        p = s.get('x').params[0]
        assert p.schema_type == 'any'

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
