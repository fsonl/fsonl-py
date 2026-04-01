"""Python-specific tests — features unique to the Python implementation"""

from fsonl import Schema
from fsonl._types import SchemaParam, SchemaDirective, ParamKind


class TestToDict:
    """SchemaParam and SchemaDirective to_dict() should return correct structures."""

    def test_schema_param_to_dict(self):
        param = SchemaParam(
            name="foo",
            kind=ParamKind.POSITIONAL,
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
            kind=ParamKind.NAMED,
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
            kind=ParamKind.POSITIONAL,
            schema_type={"kind": "array", "element": "string"},
        )
        d = param.to_dict()
        assert d["type"] == {"array": "string"}

    def test_schema_directive_to_dict(self):
        param = SchemaParam(name="a", kind=ParamKind.POSITIONAL, schema_type="string")
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
