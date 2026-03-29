"""Serialization: entries to FSONL text."""

import json
import math
import re

from ._binder import _validate_type
from ._errors import BindError

_IDENT_RE = re.compile(r'^[a-zA-Z_][a-zA-Z0-9_]*$')


def dumps(entries_or_entry, *, schema=None, allow_extra=False, exclude_schema=False):
    """Serialize entry/entries to FSONL text.

    Args:
        entries_or_entry: single entry dict or list of entry dicts
        schema: optional Schema for positional restoration
        allow_extra: if True, ignore extra keys not in schema.
                     if False (default), raise on extra keys.
        exclude_schema: if True, omit @schema lines from output.
                        if False (default), include @schema lines when schema is provided.

    Returns:
        FSONL text string with trailing newline. Empty list returns empty string.
    """
    if isinstance(entries_or_entry, list):
        if not entries_or_entry:
            return ''
        parts = []
        if schema is not None and not exclude_schema:
            for name in schema.type_names():
                parts.append(_format_schema_directive(schema.get(name)))
        parts.extend(_format_one(e, schema, allow_extra) for e in entries_or_entry)
        return '\n'.join(parts) + '\n'
    parts = []
    if schema is not None and not exclude_schema:
        for name in schema.type_names():
            parts.append(_format_schema_directive(schema.get(name)))
    parts.append(_format_one(entries_or_entry, schema, allow_extra))
    return '\n'.join(parts) + '\n'


def _format_one(entry, schema=None, allow_extra=False):
    """Format a single entry dict."""
    if not isinstance(entry, dict):
        raise TypeError(f"Unsupported entry type: {type(entry)}")
    if "positional" in entry:
        return _format_raw(entry)
    return _format_dict(entry, schema, allow_extra)


def _format_raw(entry):
    """Format a raw entry dict (with positional/named keys)."""
    _validate_identifier(entry["type"])
    parts = []
    for v in entry["positional"]:
        parts.append(_format_value(v))
    for k, v in entry["named"].items():
        if k == "type":
            raise ValueError("'type' is a reserved key and cannot be used as a named argument")
        _validate_identifier(k)
        parts.append(f"{k}={_format_value(v)}")
    return f"{entry['type']}({', '.join(parts)})"


def _format_dict(entry, schema=None, allow_extra=False):
    """Format a dict (BoundEntry)."""
    if "type" not in entry:
        raise ValueError("Entry dict must have a 'type' key")
    type_name = entry["type"]
    if not isinstance(type_name, str):
        raise TypeError(f"Entry 'type' must be a string, got {type(type_name).__name__}")
    _validate_identifier(type_name)
    parts = []

    if schema is not None and schema.has(type_name):
        directive = schema.get(type_name)
        for param in directive.params:
            if param.name not in entry:
                # Missing required → always error (positional and named)
                if not param.variadic and not param.optional and not param.has_default:
                    raise ValueError(f"Missing required field '{param.name}'")
                continue
            value = entry[param.name]
            try:
                _validate_type(value, param.schema_type, 0, param.name)
            except BindError as e:
                raise ValueError(str(e)) from None
            if param.kind == "positional" and not param.variadic:
                parts.append(_format_value(value))
            elif param.variadic:
                # Variadic: expand array as positional args
                if not isinstance(value, list):
                    raise TypeError(f"Variadic field '{param.name}' must be a list, got {type(value).__name__}")
                for v in value:
                    parts.append(_format_value(v))
            elif param.kind == "named":
                parts.append(f"{param.name}={_format_value(value)}")

        # Check for extra keys not in schema
        declared = {"type"} | {p.name for p in directive.params}
        extra = set(entry.keys()) - declared
        if extra and not allow_extra:
            raise ValueError(f"Extra keys not in schema: {', '.join(sorted(extra))}")
    else:
        # No schema: all fields as named (except type)
        for k, v in entry.items():
            if k == "type":
                continue
            _validate_identifier(k)
            parts.append(f"{k}={_format_value(v)}")

    return f"{type_name}({', '.join(parts)})"


def _format_value(value):
    """Format a single value as FSONL text."""
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, str):
        return json.dumps(value, ensure_ascii=False)
    if isinstance(value, (int, float)):
        if isinstance(value, float) and (math.isinf(value) or math.isnan(value)):
            raise ValueError(f"Cannot serialize {value} to FSONL: NaN and Infinity are not allowed")
        return json.dumps(value)
    if isinstance(value, list):
        inner = ", ".join(_format_value(v) for v in value)
        return f"[{inner}]"
    if isinstance(value, dict):
        for k in value:
            if not isinstance(k, str):
                raise TypeError(f"Object key must be a string, got {type(k).__name__}")
        inner = ", ".join(f"{json.dumps(k)}: {_format_value(v)}" for k, v in value.items())
        return f"{{{inner}}}"
    raise TypeError(f"Cannot serialize {type(value).__name__} to FSONL")


def _format_schema_directive(directive):
    """Format a SchemaDirective as an @schema line."""
    params = ", ".join(_format_schema_param(p) for p in directive.params)
    return f"@schema {directive.name}({params})"


def _format_schema_param(param):
    """Format a single SchemaParam."""
    prefix = ""
    suffix = ""

    if param.variadic:
        prefix = "*"
    elif param.kind == "named":
        prefix = "--"

    name = f"{prefix}{param.name}"

    if param.optional and not param.has_default:
        name += "?"

    type_str = _format_schema_type(param.schema_type)
    result = f"{name}: {type_str}"

    if param.has_default:
        result += f" = {_format_value(param.default)}"

    return result


def _format_schema_type(schema_type):
    """Format a schema type back to its text representation."""
    if isinstance(schema_type, str):
        return schema_type
    if isinstance(schema_type, dict):
        kind = schema_type.get("kind")
        if kind == "array":
            element = schema_type["element"]
            inner = _format_schema_type(element)
            if isinstance(element, dict) and element.get("kind") == "union":
                return f"({inner})[]"
            return f"{inner}[]"
        elif kind == "union":
            return " | ".join(_format_schema_type(t) for t in schema_type["types"])
        elif kind == "object":
            fields = []
            for f in schema_type["fields"]:
                fname = f["name"]
                if f.get("optional", False):
                    fname += "?"
                fields.append(f"{fname}: {_format_schema_type(f['type'])}")
            return "{ " + ", ".join(fields) + " }"
    return str(schema_type)


def _validate_identifier(name):
    """Validate that a name is a valid FSONL identifier [a-zA-Z_][a-zA-Z0-9_]*."""
    if not _IDENT_RE.match(name):
        raise ValueError(f"Invalid FSONL identifier: {name!r}")
