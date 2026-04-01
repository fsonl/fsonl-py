"""Public API: loads, load, loads_raw, iter_entries, iter_raw, bind, dumps."""
from __future__ import annotations

from typing import Any, Iterator, List, Optional, Union
from typing import IO

from ._parser import parse_document_items, _prepare_file_lines, _parse_items
from ._types import ParseResult, RawEntry, ExtraFieldPolicy, SchemaDirective
from ._schema import Schema
from ._binder import bind_entry
from ._errors import SchemaError, BindError
from ._serializer import dumps as _dumps


def _process_items(items, *, schema=None, ignore_inline_schema=False,
                   extra_fields=ExtraFieldPolicy.ERROR, file_schema=None):
    """Core processing loop for bind mode.

    Yields bound entries. Mutates file_schema in place if provided.
    """
    if file_schema is None:
        file_schema = Schema()

    for item in items:
        if isinstance(item, SchemaDirective):
            file_schema._add_directive(item)

            if schema is not None and not ignore_inline_schema and schema.has(item.name):
                _cross_validate(schema.get(item.name), item)
        else:
            line = item.get("_line", 0)
            type_name = item["type"]

            entry_schema = _resolve_schema(type_name, schema, file_schema,
                                           ignore_inline_schema)

            if entry_schema is not None:
                directive = entry_schema.get(type_name)
                yield bind_entry(item, directive, line_number=line, extra_fields=extra_fields)
            else:
                raise BindError(line, f"No schema for type '{type_name}'")


def _process_items_raw(items) -> Iterator[RawEntry]:
    """Core processing loop for raw mode. Yields RawEntry objects."""
    for item in items:
        if not isinstance(item, SchemaDirective):
            yield RawEntry(
                type=item["type"],
                positional=item["positional"],
                named=item["named"],
                _line=item.get("_line", 0),
            )


# ── Bind mode ──

def loads(
    text: str,
    *,
    schema: Optional[Schema] = None,
    ignore_inline_schema: bool = False,
    extra_fields: ExtraFieldPolicy = ExtraFieldPolicy.ERROR,
) -> ParseResult:
    """Parse FSONL text with schema binding.

    Returns:
        ParseResult with bound entries and schema
    """
    # Consume all parsed items first so parser-level errors (syntax_error,
    # schema_error) take priority over binding errors (bind_error).
    items = list(parse_document_items(text))

    file_schema = Schema()
    entries = list(_process_items(
        items, schema=schema, ignore_inline_schema=ignore_inline_schema,
        extra_fields=extra_fields, file_schema=file_schema))

    return ParseResult(entries, file_schema)


def load(
    fp: IO[str],
    *,
    schema: Optional[Schema] = None,
    ignore_inline_schema: bool = False,
    extra_fields: ExtraFieldPolicy = ExtraFieldPolicy.ERROR,
) -> ParseResult:
    """Parse FSONL from a file object with schema binding.

    Note: open with newline='' to preserve bare \\r detection.
    """
    return loads(fp.read(), schema=schema, ignore_inline_schema=ignore_inline_schema,
                 extra_fields=extra_fields)


def iter_entries(
    source: Union[str, IO[str]],
    *,
    schema: Optional[Schema] = None,
    ignore_inline_schema: bool = False,
    extra_fields: ExtraFieldPolicy = ExtraFieldPolicy.ERROR,
) -> Iterator[Any]:
    """Lazily iterate over bound entries from a string or file object.

    Note: open file objects with newline='' to preserve bare \\r detection.
    """
    if hasattr(source, 'read'):
        items = _parse_items(_prepare_file_lines(source))
    else:
        items = parse_document_items(source)

    yield from _process_items(
        items, schema=schema, ignore_inline_schema=ignore_inline_schema,
        extra_fields=extra_fields)


# ── Raw mode ──

def loads_raw(text: str) -> ParseResult:
    """Parse FSONL text without schema binding (Stage 1 only).

    Returns:
        ParseResult with RawEntry objects and file schema (if any)
    """
    items = list(parse_document_items(text))
    file_schema = Schema()
    entries: List[RawEntry] = []
    for item in items:
        if isinstance(item, SchemaDirective):
            file_schema._add_directive(item)
        else:
            entries.append(RawEntry(
                type=item["type"],
                positional=item["positional"],
                named=item["named"],
                _line=item.get("_line", 0),
            ))
    return ParseResult(entries, file_schema)


def load_raw(fp: IO[str]) -> ParseResult:
    """Parse FSONL from a file object without schema binding (Stage 1 only).

    Note: open with newline='' to preserve bare \\r detection.
    """
    return loads_raw(fp.read())


def iter_raw(source: Union[str, IO[str]]) -> Iterator[RawEntry]:
    """Lazily iterate over RawEntry objects from a string or file object.

    Note: open file objects with newline='' to preserve bare \\r detection.
    """
    if hasattr(source, 'read'):
        items = _parse_items(_prepare_file_lines(source))
    else:
        items = parse_document_items(source)

    yield from _process_items_raw(items)


# ── Single entry ──

def bind(
    entry: RawEntry,
    schema: Schema,
    *,
    line: Optional[int] = None,
    extra_fields: ExtraFieldPolicy = ExtraFieldPolicy.ERROR,
) -> Any:
    """Bind a single RawEntry to a Schema."""
    type_name = entry["type"]
    resolved_line: int = line if line is not None else entry.get("_line", 0)
    if not schema.has(type_name):
        raise BindError(resolved_line, f"No schema for type '{type_name}'")
    directive = schema.get(type_name)
    return bind_entry(entry, directive, line_number=resolved_line, extra_fields=extra_fields)


# ── Serialization ──

def dump(
    entries: list,
    fp: IO[str],
    *,
    schema: Optional[Schema] = None,
    allow_extra: bool = False,
    exclude_schema: bool = False,
) -> None:
    """Serialize entries to FSONL and write to a file object."""
    if not isinstance(entries, list):
        raise TypeError("dump() requires a list of entries")
    fp.write(_dumps(entries, schema=schema, allow_extra=allow_extra,
                    exclude_schema=exclude_schema))


def dumps(
    entries: list,
    *,
    schema: Optional[Schema] = None,
    allow_extra: bool = False,
    exclude_schema: bool = False,
) -> str:
    """Serialize entries to FSONL text."""
    return _dumps(entries, schema=schema, allow_extra=allow_extra,
                  exclude_schema=exclude_schema)


# ── Internal ──

def _resolve_schema(type_name, code_schema, file_schema, ignore_inline_schema):
    """Resolve which schema to use for a given type."""
    has_code = code_schema is not None and code_schema.has(type_name)
    has_file = file_schema.has(type_name)

    if has_code:
        return code_schema
    elif has_file and not ignore_inline_schema:
        return file_schema
    else:
        return None


def _cross_validate(code_directive, file_directive):
    """Cross-validate code schema and file schema directives."""
    code_params = code_directive.params
    file_params = file_directive.params
    line = file_directive.line

    if len(code_params) != len(file_params):
        raise SchemaError(line,
            f"Parameter count mismatch: @schema has {len(file_params)}, "
            f"code has {len(code_params)}")

    for i, (fp, cp) in enumerate(zip(file_params, code_params)):
        if fp.name != cp.name:
            raise SchemaError(line,
                f"Parameter {i} name mismatch: @schema '{fp.name}', code '{cp.name}'")

        if fp.kind != cp.kind:
            raise SchemaError(line,
                f"Parameter '{fp.name}' kind mismatch: @schema '{fp.kind.value}', code '{cp.kind.value}'")

        if _normalize_type(fp.schema_type) != _normalize_type(cp.schema_type):
            raise SchemaError(line,
                f"Parameter '{fp.name}' type mismatch")

        if fp.optional != cp.optional:
            raise SchemaError(line,
                f"Parameter '{fp.name}' optional mismatch")

        if fp.variadic != cp.variadic:
            raise SchemaError(line,
                f"Parameter '{fp.name}' variadic mismatch")

        if fp.has_default != cp.has_default:
            raise SchemaError(line,
                f"Parameter '{fp.name}' default presence mismatch")

        if fp.has_default and cp.has_default and fp.default != cp.default:
            raise SchemaError(line,
                f"Parameter '{fp.name}' default value mismatch")


def _normalize_type(schema_type):
    """Normalize a schema type for comparison."""
    if isinstance(schema_type, str):
        return schema_type
    if isinstance(schema_type, dict):
        kind = schema_type.get("kind")
        if kind == "array":
            return ("array", _normalize_type(schema_type["element"]))
        elif kind == "union":
            return ("union", frozenset(_normalize_type(t) for t in schema_type["types"]))
        elif kind == "object":
            return ("object", frozenset(
                (f["name"], _normalize_type(f["type"]), f.get("optional", False))
                for f in schema_type["fields"]
            ))
    return schema_type
