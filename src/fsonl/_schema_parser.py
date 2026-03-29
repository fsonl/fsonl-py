"""@schema line parser (Stage 1 syntax parsing of schema directives)."""

from ._errors import ParseError
from ._scanner import skip_ws, read_identifier, looks_like_identifier, expect, _is_ident_char
from ._values import parse_value
from ._types import SchemaDirective, SchemaParam


def parse_schema_line(line, pos, line_number):
    """Parse a @schema line. pos points right after '@schema'.
    Returns a SchemaDirective."""
    # @schema must be followed by whitespace
    if pos >= len(line) or line[pos] not in (' ', '\t'):
        raise ParseError(line_number, "Expected space after @schema")
    pos = skip_ws(line, pos)
    return _parse_schema_body(line, pos, line_number)


def parse_schema_bare(line, pos, line_number):
    """Parse a bare schema definition (without @schema prefix).
    pos points at the type name. Returns a SchemaDirective."""
    return _parse_schema_body(line, pos, line_number)


def _parse_schema_body(line, pos, line_number):
    """Parse schema body starting from type name."""
    # Type name
    type_name, pos = read_identifier(line, pos, line_number)
    pos = expect(line, pos, '(', line_number)

    # Parameter list
    params = []
    param_names = set()
    pos = skip_ws(line, pos)
    if pos < len(line) and line[pos] != ')':
        while True:
            param, pos = _parse_schema_param(line, pos, line_number)
            # Validate: param name cannot be "type"
            if param.name == "type":
                raise ParseError(line_number, "'type' is reserved")
            # Validate: no duplicate param names
            if param.name in param_names:
                raise ParseError(line_number, f"Duplicate parameter name '{param.name}'")
            param_names.add(param.name)
            params.append(param)
            pos = skip_ws(line, pos)
            if pos < len(line) and line[pos] == ',':
                pos += 1
                pos = skip_ws(line, pos)
                continue
            elif pos < len(line) and line[pos] == ')':
                break
            else:
                raise ParseError(line_number, "Expected ',' or ')' in @schema params")

    pos = expect(line, pos, ')', line_number)

    # Validate: variadic must be last positional, and only one
    _validate_schema_params(params, line_number)

    # Check trailing
    _check_trailing(line, pos, line_number)

    return SchemaDirective(type_name, params, line_number)


def _parse_schema_param(line, pos, line_number):
    """Parse a single schema parameter."""
    pos = skip_ws(line, pos)

    if pos < len(line) and line[pos] == '*':
        # Variadic: *name: type[]
        pos += 1
        name, pos = read_identifier(line, pos, line_number)
        pos = skip_ws(line, pos)
        pos = expect(line, pos, ':', line_number)
        pos = skip_ws(line, pos)
        schema_type, pos = _parse_schema_type(line, pos, line_number)
        # Variadic must be array type
        if not (isinstance(schema_type, dict) and schema_type.get("kind") == "array"):
            raise ParseError(line_number, "Variadic parameter must have array type")
        return SchemaParam(name, "positional", schema_type, variadic=True), pos

    elif pos + 1 < len(line) and line[pos:pos + 2] == '--':
        # Named: --name?: type = default
        pos += 2
        name, pos = read_identifier(line, pos, line_number)
        optional = False
        if pos < len(line) and line[pos] == '?':
            optional = True
            pos += 1
        pos = skip_ws(line, pos)
        pos = expect(line, pos, ':', line_number)
        pos = skip_ws(line, pos)
        schema_type, pos = _parse_schema_type(line, pos, line_number)

        has_default = False
        default = None
        pos = skip_ws(line, pos)
        if pos < len(line) and line[pos] == '=':
            pos += 1
            pos = skip_ws(line, pos)
            default, pos = parse_value(line, pos, line_number)
            has_default = True
            optional = True  # default implies optional
            # Validate default value against declared type
            if not _check_default_type(default, schema_type):
                raise ParseError(line_number, f"Default value for '{name}' does not match declared type")

        return SchemaParam(name, "named", schema_type, optional=optional,
                           has_default=has_default, default=default), pos

    else:
        # Positional: name: type
        name, pos = read_identifier(line, pos, line_number)
        pos = skip_ws(line, pos)
        pos = expect(line, pos, ':', line_number)
        pos = skip_ws(line, pos)
        schema_type, pos = _parse_schema_type(line, pos, line_number)
        return SchemaParam(name, "positional", schema_type), pos


def _parse_schema_type(line, pos, line_number):
    """Parse a schema type expression, including unions."""
    stype, pos = _parse_single_type(line, pos, line_number)
    types = [stype]

    while True:
        pos2 = skip_ws(line, pos)
        if pos2 < len(line) and line[pos2] == '|':
            pos = skip_ws(line, pos2 + 1)
            stype, pos = _parse_single_type(line, pos, line_number)
            types.append(stype)
        else:
            break

    if len(types) == 1:
        return types[0], pos
    return {"kind": "union", "types": types}, pos


def _parse_single_type(line, pos, line_number):
    """Parse a single type (primitive, object, or parenthesized union), with optional [] suffix."""
    if pos < len(line) and line[pos] == '{':
        stype, pos = _parse_object_type(line, pos, line_number)
    elif pos < len(line) and line[pos] == '(':
        # Parenthesized union for array base: (string | number)[]
        pos += 1
        pos = skip_ws(line, pos)
        stype, pos = _parse_schema_type(line, pos, line_number)
        pos = skip_ws(line, pos)
        pos = expect(line, pos, ')', line_number)
    else:
        stype, pos = _parse_primitive_type(line, pos, line_number)

    # Array suffix: [][]...
    while pos + 1 < len(line) and line[pos:pos + 2] == '[]':
        stype = {"kind": "array", "element": stype}
        pos += 2

    return stype, pos


def _parse_primitive_type(line, pos, line_number):
    """Parse a primitive type keyword."""
    for keyword in ("string", "number", "bool", "null", "any"):
        end = pos + len(keyword)
        if line[pos:end] == keyword:
            # Word boundary check
            if end < len(line) and _is_ident_char(line[end]):
                continue
            return keyword, end
    raise ParseError(line_number, f"Unknown type at position {pos}")


def _parse_object_type(line, pos, line_number):
    """Parse an object type: { name: type, name?: type }"""
    pos = expect(line, pos, '{', line_number)
    pos = skip_ws(line, pos)

    fields = []
    field_names = set()
    if pos < len(line) and line[pos] != '}':
        while True:
            name, pos = read_identifier(line, pos, line_number)
            if name in field_names:
                raise ParseError(line_number, f"Duplicate field name '{name}' in object type")
            field_names.add(name)
            optional = False
            if pos < len(line) and line[pos] == '?':
                optional = True
                pos += 1
            pos = skip_ws(line, pos)
            pos = expect(line, pos, ':', line_number)
            pos = skip_ws(line, pos)
            ftype, pos = _parse_schema_type(line, pos, line_number)
            fields.append({"name": name, "optional": optional, "type": ftype})
            pos = skip_ws(line, pos)
            if pos < len(line) and line[pos] == ',':
                pos += 1
                pos = skip_ws(line, pos)
                continue
            elif pos < len(line) and line[pos] == '}':
                break
            else:
                raise ParseError(line_number, "Expected ',' or '}' in object type")

    pos = expect(line, pos, '}', line_number)
    return {"kind": "object", "fields": fields}, pos


def _validate_schema_params(params, line_number):
    """Validate schema parameter constraints."""
    # Positional params must come before named params
    seen_named = False
    for p in params:
        if p.kind == "named":
            seen_named = True
        elif p.kind == "positional" and seen_named:
            raise ParseError(line_number, "Positional parameter after named parameter")

    # Variadic must be the last positional
    found_variadic = False
    for p in params:
        if found_variadic and p.kind == "positional":
            raise ParseError(line_number, "Variadic parameter must be last positional")
        if p.variadic:
            found_variadic = True


def _check_trailing(line, pos, line_number):
    """Check that only whitespace and // comments follow."""
    pos = skip_ws(line, pos)
    if pos >= len(line):
        return
    if line[pos:pos + 2] == '//':
        return
    raise ParseError(line_number, f"Unexpected content after ')' at position {pos}")


def _check_default_type(value, schema_type):
    """Check if a default value matches a schema type. Returns True/False."""
    if isinstance(schema_type, str):
        if schema_type == "any":
            return True
        if schema_type == "string":
            return isinstance(value, str)
        if schema_type == "number":
            return isinstance(value, (int, float)) and not isinstance(value, bool)
        if schema_type == "bool":
            return isinstance(value, bool)
        if schema_type == "null":
            return value is None
        return True
    if isinstance(schema_type, dict):
        kind = schema_type.get("kind")
        if kind == "array":
            if not isinstance(value, list):
                return False
            element = schema_type.get("element")
            return element is None or all(_check_default_type(v, element) for v in value)
        if kind == "union":
            return any(_check_default_type(value, t) for t in schema_type.get("types", []))
        if kind == "object":
            if not isinstance(value, dict):
                return False
            fields = schema_type.get("fields", [])
            for f in fields:
                if f["name"] in value:
                    if not _check_default_type(value[f["name"]], f["type"]):
                        return False
                elif not f.get("optional", False):
                    return False
            return True
    return True
