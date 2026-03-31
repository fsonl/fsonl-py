"""Common API tests — all language implementations should have equivalent tests.

Covers: dumps() with schema validation — missing required fields, extra key
detection, allow_extra=True behavior. Extra keys with allow_extra=True should
be serialized as named parameters (not silently dropped).
"""

import pytest
from fsonl import dumps, Schema


@pytest.fixture
def schema():
    return Schema.from_string('@schema x(a: string, --b: number)')


@pytest.fixture
def variadic_schema():
    return Schema.from_string('@schema y(*msg: string[])')


class TestDefault:
    """Default (allow_extra=False): reject missing required fields and extra keys."""

    def test_missing_required_positional(self, schema):
        with pytest.raises(ValueError, match="Missing required field 'a'"):
            dumps({"type": "x", "b": 1}, schema=schema)

    def test_missing_required_named(self, schema):
        with pytest.raises(ValueError, match="Missing required field 'b'"):
            dumps({"type": "x", "a": "ok"}, schema=schema)

    def test_extra_keys(self, schema):
        with pytest.raises(ValueError, match="Extra keys"):
            dumps({"type": "x", "a": "ok", "b": 1, "extra": 2}, schema=schema)

    def test_valid_entry(self, schema):
        assert dumps({"type": "x", "a": "ok", "b": 1}, schema=schema) == '@schema x(a: string, --b: number)\nx("ok", b=1)\n'

    def test_variadic_non_list(self, variadic_schema):
        with pytest.raises(ValueError, match="expected array"):
            dumps({"type": "y", "msg": "not-list"}, schema=variadic_schema)


class TestAllowExtra:
    """allow_extra=True: extra keys are serialized as named params, missing required still errors."""

    def test_missing_required_positional_still_errors(self, schema):
        with pytest.raises(ValueError, match="Missing required field 'a'"):
            dumps({"type": "x", "b": 1}, schema=schema, allow_extra=True)

    def test_missing_required_named_still_errors(self, schema):
        with pytest.raises(ValueError, match="Missing required field 'b'"):
            dumps({"type": "x", "a": "ok"}, schema=schema, allow_extra=True)

    @pytest.mark.xfail(reason="Serializer drops extra keys with allow_extra=True — should serialize them")
    def test_extra_keys_serialized_as_named(self, schema):
        # Extra fields should be serialized as named parameters, not dropped
        result = dumps({"type": "x", "a": "ok", "b": 1, "extra": 2}, schema=schema, allow_extra=True)
        assert '@schema x(a: string, --b: number)\n' in result
        assert 'x("ok", b=1, extra=2)\n' in result

    def test_optional_named_omitted(self):
        s = Schema.from_string('@schema z(a: string, --b?: number)')
        assert dumps({"type": "z", "a": "ok"}, schema=s, allow_extra=True) == '@schema z(a: string, --b?: number)\nz("ok")\n'

    def test_default_named_omitted(self):
        s = Schema.from_string('@schema z(a: string, --b: number = 0)')
        assert dumps({"type": "z", "a": "ok"}, schema=s, allow_extra=True) == '@schema z(a: string, --b: number = 0)\nz("ok")\n'


class TestNoSchema:
    """Without schema, allow_extra has no effect on validation."""

    def test_no_schema_all_named(self):
        assert dumps({"type": "x", "a": "ok"}) == 'x(a="ok")\n'

    def test_no_schema_allow_extra_same(self):
        assert dumps({"type": "x", "a": "ok"}, allow_extra=True) == 'x(a="ok")\n'
