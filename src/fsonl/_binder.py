"""Stage 2 binder: bind raw entry dict to SchemaDirective."""

import copy

from ._errors import BindError
from ._types import ExtraFieldPolicy, ParamKind


def bind_entry(raw_entry, schema_directive, line_number=None, extra_fields=ExtraFieldPolicy.ERROR):
    """Bind a raw entry dict to a SchemaDirective, returning a flat dict.

    Args:
        raw_entry: dict with type, positional, named (and optional _line)
        schema_directive: SchemaDirective with params list
        line_number: line number for errors (default: raw_entry["_line"] or 0)
        extra_fields: policy for undeclared named arguments at entry level

    Returns:
        dict with "type" key and bound parameter values
    """
    if line_number is None:
        line_number = raw_entry.get("_line", 0)

    positional = raw_entry["positional"]
    named = raw_entry["named"]

    result = {"type": raw_entry["type"]}
    positional_idx = 0
    has_variadic = any(p.variadic for p in schema_directive.params)

    for param in schema_directive.params:
        if param.kind == ParamKind.POSITIONAL and not param.variadic:
            # Regular positional parameter
            if positional_idx < len(positional):
                value = positional[positional_idx]
                value = _validate_type(value, param.schema_type, line_number, param.name)
                result[param.name] = value
                positional_idx += 1
            elif param.has_default:
                result[param.name] = copy.deepcopy(param.default) if isinstance(param.default, (list, dict)) else param.default
            elif param.optional:
                pass
            else:
                raise BindError(line_number, f"Missing required positional argument '{param.name}'")

        elif param.kind == ParamKind.POSITIONAL and param.variadic:
            # Variadic: consume all remaining positional args
            remaining = positional[positional_idx:]
            element_type = param.schema_type.get("element") if isinstance(param.schema_type, dict) else None
            if element_type is not None:
                remaining = [_validate_type(v, element_type, line_number, param.name) for v in remaining]
            result[param.name] = remaining
            positional_idx = len(positional)

        elif param.kind == ParamKind.NAMED:
            if param.name in named:
                value = named[param.name]
                value = _validate_type(value, param.schema_type, line_number, param.name)
                result[param.name] = value
            elif param.has_default:
                result[param.name] = copy.deepcopy(param.default) if isinstance(param.default, (list, dict)) else param.default
            elif param.optional:
                pass
            else:
                raise BindError(line_number, f"Missing required named argument '{param.name}'")

    # Check for excess positional args (only when no variadic)
    if positional_idx < len(positional) and not has_variadic:
        raise BindError(line_number, f"Too many positional arguments: expected {positional_idx}, got {len(positional)}")

    # Check for undeclared named args — policy driven by extra_fields
    declared_named = set(p.name for p in schema_directive.params if p.kind == ParamKind.NAMED)
    extra_keys = set(named.keys()) - declared_named
    if extra_keys:
        if extra_fields == ExtraFieldPolicy.ERROR:
            raise BindError(line_number, f"Undeclared named argument '{sorted(extra_keys)[0]}'")
        elif extra_fields == ExtraFieldPolicy.PRESERVE:
            for k in extra_keys:
                result[k] = named[k]
        # STRIP: silently ignore

    return result


def _validate_type(value, schema_type, line_number, param_name=""):
    """Validate that a value matches a schema type.

    Returns the (possibly cleaned) value.
    """
    if isinstance(schema_type, str):
        _validate_primitive(value, schema_type, line_number, param_name)
        return value
    elif isinstance(schema_type, dict):
        kind = schema_type.get("kind")
        if kind == "array":
            return _validate_array(value, schema_type, line_number, param_name)
        elif kind == "object":
            return _validate_object(value, schema_type, line_number, param_name)
        elif kind == "union":
            return _validate_union(value, schema_type, line_number, param_name)
    return value


def _validate_primitive(value, type_name, line_number, param_name):
    """Validate a value against a primitive type."""
    if type_name == "any":
        return
    elif type_name == "string":
        if not isinstance(value, str):
            raise BindError(line_number, f"Type mismatch for '{param_name}': expected string, got {_type_label(value)}")
    elif type_name == "number":
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            raise BindError(line_number, f"Type mismatch for '{param_name}': expected number, got {_type_label(value)}")
    elif type_name == "bool":
        if not isinstance(value, bool):
            raise BindError(line_number, f"Type mismatch for '{param_name}': expected bool, got {_type_label(value)}")
    elif type_name == "null":
        if value is not None:
            raise BindError(line_number, f"Type mismatch for '{param_name}': expected null, got {_type_label(value)}")


def _validate_array(value, schema_type, line_number, param_name):
    """Validate a value against an array type."""
    if not isinstance(value, list):
        raise BindError(line_number, f"Type mismatch for '{param_name}': expected array, got {_type_label(value)}")
    element_type = schema_type.get("element")
    if element_type is not None:
        return [_validate_type(item, element_type, line_number, param_name) for item in value]
    return value


def _validate_object(value, schema_type, line_number, param_name):
    """Validate a value against an object type. Always strict — undeclared fields are errors."""
    if not isinstance(value, dict):
        raise BindError(line_number, f"Type mismatch for '{param_name}': expected object, got {_type_label(value)}")

    fields = schema_type.get("fields", [])
    declared_names = {f["name"] for f in fields}
    result = {}

    for field in fields:
        fname = field["name"]
        if fname in value:
            result[fname] = _validate_type(value[fname], field["type"], line_number, f"{param_name}.{fname}")
        elif not field.get("optional", False):
            raise BindError(line_number, f"Missing required field '{fname}' in object for '{param_name}'")

    extra_keys = set(value.keys()) - declared_names
    if extra_keys:
        raise BindError(line_number, f"Undeclared field(s) {', '.join(sorted(extra_keys))} in object for '{param_name}'")

    return result


def _validate_union(value, schema_type, line_number, param_name):
    """Validate a value against a union type.

    For object branches, prefer the branch whose declared field names overlap
    most with the value's keys, to avoid the first all-optional branch
    consuming values intended for a later branch.
    Uses deep copy for object/array types to prevent mutation during trial matching.
    """
    types = schema_type.get("types", [])

    candidates = []
    for t in types:
        try:
            trial = copy.deepcopy(value) if isinstance(value, (dict, list)) else value
            result = _validate_type(trial, t, line_number, param_name)
            if isinstance(value, dict) and isinstance(t, dict) and t.get("kind") == "object":
                declared = set(f["name"] for f in t.get("fields", []))
                score = len(declared & set(value.keys()))
            else:
                score = 0
            candidates.append((score, result))
        except BindError:
            continue

    if not candidates:
        raise BindError(line_number, f"Type mismatch for '{param_name}': value does not match any union type")

    best_score = max(c[0] for c in candidates)
    for score, result in candidates:
        if score == best_score:
            return result


def _type_label(value):
    """Get a human-readable type label for a value."""
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "bool"
    if isinstance(value, int):
        return "number"
    if isinstance(value, float):
        return "number"
    if isinstance(value, str):
        return "string"
    if isinstance(value, list):
        return "array"
    if isinstance(value, dict):
        return "object"
    return type(value).__name__
