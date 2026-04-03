"""Convert Python function signatures to SchemaDirective (Python 3.10+)."""

import inspect
import types
import typing
from typing import Union, get_origin, get_args

from ._types import SchemaDirective, SchemaParam, ParamKind, OMIT


# Python type → FSONL type string
_PRIMITIVE_MAP = {
    str: "string",
    int: "number",
    float: "number",
    bool: "bool",
}


def _fn_to_directive(fn):
    """Convert a function's signature and annotations to a SchemaDirective."""
    sig = inspect.signature(fn)
    hints = typing.get_type_hints(fn)
    params = []

    for name, param in sig.parameters.items():
        # F1: reject 'type' as parameter name (§7, §9.1)
        if name == "type":
            raise TypeError("'type' is reserved and cannot be used as a parameter name")

        # F4: reject **kwargs — FSONL has no arbitrary named remainder
        if param.kind == inspect.Parameter.VAR_KEYWORD:
            raise TypeError(f"**{name} (VAR_KEYWORD) is not supported in FSONL schema definitions")

        if param.kind == inspect.Parameter.VAR_POSITIONAL:
            # *args → variadic
            ann = hints.get(name)
            if ann is None:
                raise TypeError(f"Variadic parameter '{name}' must have a type annotation")
            element_type = _python_type_to_schema(ann)
            schema_type = {"kind": "array", "element": element_type}
            params.append(SchemaParam(
                name=name, kind=ParamKind.POSITIONAL, schema_type=schema_type,
                optional=False, variadic=True,
            ))

        elif param.kind in (inspect.Parameter.POSITIONAL_ONLY,
                            inspect.Parameter.POSITIONAL_OR_KEYWORD):
            # positional
            ann = hints.get(name)
            if ann is None:
                raise TypeError(f"Parameter '{name}' must have a type annotation")
            schema_type = _python_type_to_schema(ann)
            is_omit = param.default is OMIT
            has_default = param.default is not inspect.Parameter.empty and not is_omit
            params.append(SchemaParam(
                name=name, kind=ParamKind.POSITIONAL, schema_type=schema_type,
                optional=has_default or is_omit, has_default=has_default,
                default=param.default if has_default else None,
            ))

        elif param.kind == inspect.Parameter.KEYWORD_ONLY:
            # named
            ann = hints.get(name)
            if ann is None:
                raise TypeError(f"Parameter '{name}' must have a type annotation")
            schema_type = _python_type_to_schema(ann)
            is_omit = param.default is OMIT
            has_default = param.default is not inspect.Parameter.empty and not is_omit
            params.append(SchemaParam(
                name=name, kind=ParamKind.NAMED, schema_type=schema_type,
                optional=has_default or is_omit, has_default=has_default,
                default=param.default if has_default else None,
            ))

    return SchemaDirective(fn.__name__, params, line=0)


def _python_type_to_schema(ann):
    """Convert a Python type annotation to FSONL schema type."""
    # NoneType
    if ann is type(None):
        return "null"

    # Any
    if ann is typing.Any:
        return "any"

    # dict → any (arbitrary JSON object)
    if ann is dict:
        return "any"

    # Primitives
    if ann in _PRIMITIVE_MAP:
        return _PRIMITIVE_MAP[ann]

    origin = get_origin(ann)
    args = get_args(ann)

    # dict[K, V] → any (FSONL has no map type)
    if origin is dict:
        return "any"

    # list[X] → array
    if origin is list:
        if not args:
            return {"kind": "array", "element": "any"}
        return {"kind": "array", "element": _python_type_to_schema(args[0])}

    # Union (str | None, Union[str, int], etc.)
    if origin is Union or isinstance(ann, types.UnionType):
        if not args:
            args = ann.__args__
        union_types = [_python_type_to_schema(a) for a in args]
        if len(union_types) == 1:
            return union_types[0]
        return {"kind": "union", "types": union_types}

    raise TypeError(f"Unsupported type annotation: {ann}")
