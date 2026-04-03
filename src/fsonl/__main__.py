"""CLI entry point:
  fsonl parse [--raw|--schema] [--define '...'] [--extra-fields error|preserve|strip]
  fsonl serialize [--raw] [--define '...'] [--allow-extra] [--exclude-schema]
"""

import sys
import json

from ._parser import parse_document_items
from ._types import SchemaDirective, RawEntry
from ._schema import Schema
from ._types import ExtraFieldPolicy
from ._api import loads, loads_raw
from ._serializer import dumps as _dumps
from . import _errors

_EXTRA_FIELD_VALUES = {p.value: p for p in ExtraFieldPolicy}

_USAGE = """\
Usage:
  fsonl parse [--raw|--schema] [--define '...'] [--extra-fields error|preserve|strip]
  fsonl serialize [--raw] [--define '...'] [--allow-extra] [--exclude-schema]"""


def _parse_args(argv):
    """Parse CLI arguments, extracting subcommand and flags."""
    args = argv[1:]
    if not args or args[0] not in ("parse", "serialize"):
        print(_USAGE, file=sys.stderr)
        sys.exit(1)

    subcommand = args[0]

    if subcommand == "parse":
        return _parse_parse_args(args[1:])
    else:
        return _parse_serialize_args(args[1:])


def _parse_parse_args(args):
    """Parse arguments for the 'parse' subcommand."""
    mode_flags = set()
    defines = []
    extra_fields = ExtraFieldPolicy.ERROR
    i = 0
    while i < len(args):
        if args[i] == "--define":
            if i + 1 >= len(args):
                print("Error: --define requires a value", file=sys.stderr)
                sys.exit(1)
            defines.append(args[i + 1])
            i += 2
        elif args[i] == "--extra-fields":
            if i + 1 >= len(args):
                print("Error: --extra-fields requires a value (error|preserve|strip)", file=sys.stderr)
                sys.exit(1)
            val = args[i + 1]
            if val not in _EXTRA_FIELD_VALUES:
                print("Error: --extra-fields must be one of: error, preserve, strip", file=sys.stderr)
                sys.exit(1)
            extra_fields = _EXTRA_FIELD_VALUES[val]
            i += 2
        elif args[i] in ("--raw", "--schema"):
            mode_flags.add(args[i])
            i += 1
        else:
            print(f"Error: unknown flag: {args[i]}", file=sys.stderr)
            sys.exit(1)

    if len(mode_flags) > 1:
        print("Error: --raw, --schema are mutually exclusive", file=sys.stderr)
        sys.exit(1)

    if "--raw" in mode_flags:
        mode = "raw"
    elif "--schema" in mode_flags:
        mode = "schema"
    else:
        mode = "bind"

    code_schema = None
    if defines:
        code_schema = Schema()
        for d in defines:
            code_schema.add(d)

    return "parse", mode, code_schema, extra_fields, False, False


def _parse_serialize_args(args):
    """Parse arguments for the 'serialize' subcommand."""
    raw = False
    defines = []
    allow_extra = False
    exclude_schema = False
    i = 0
    while i < len(args):
        if args[i] == "--raw":
            raw = True
            i += 1
        elif args[i] == "--define":
            if i + 1 >= len(args):
                print("Error: --define requires a value", file=sys.stderr)
                sys.exit(1)
            defines.append(args[i + 1])
            i += 2
        elif args[i] == "--allow-extra":
            allow_extra = True
            i += 1
        elif args[i] == "--exclude-schema":
            exclude_schema = True
            i += 1
        else:
            print(f"Error: unknown flag: {args[i]}", file=sys.stderr)
            sys.exit(1)

    code_schema = None
    if defines:
        code_schema = Schema()
        for d in defines:
            code_schema.add(d)

    mode = "raw" if raw else "bind"
    return "serialize", mode, code_schema, None, allow_extra, exclude_schema


def _serialize_error(line: int, message: str):
    """Print a serialize error and exit."""
    print(f"serialize_error:{line}", file=sys.stderr)
    print(message, file=sys.stderr)
    sys.exit(1)


def _serialize_main(mode, code_schema, allow_extra, exclude_schema):
    """Handle the serialize subcommand."""
    text = sys.stdin.read()
    lines = [line for line in text.splitlines() if line.strip()]

    if not lines:
        return

    entries = []
    for line_num, line in enumerate(lines, 1):
        # Parse JSONL
        try:
            obj = json.loads(line)
        except json.JSONDecodeError as e:
            _serialize_error(line_num, f"Invalid JSON: {e}")

        if not isinstance(obj, dict):
            _serialize_error(line_num, f"Expected JSON object, got {type(obj).__name__}")

        # Validate type field
        if "type" not in obj:
            _serialize_error(line_num, "Missing 'type' key")

        if not isinstance(obj["type"], str):
            _serialize_error(line_num, f"'type' must be a string, got {type(obj['type']).__name__}")

        if mode == "raw":
            # Validate raw shape
            if "positional" not in obj:
                _serialize_error(line_num, "Raw entry missing 'positional' key")
            if "named" not in obj:
                _serialize_error(line_num, "Raw entry missing 'named' key")
            entry = RawEntry(
                type=obj["type"],
                positional=obj["positional"],
                named=obj["named"],
            )
        else:
            entry = obj

        entries.append((line_num, entry))

    # Serialize
    entry_list = [e for _, e in entries]
    try:
        result = _dumps(
            entry_list,
            schema=code_schema,
            allow_extra=allow_extra,
            exclude_schema=exclude_schema,
        )
    except (ValueError, TypeError) as e:
        # Try to find which entry caused the error by serializing one at a time
        for line_num, entry in entries:
            try:
                _dumps([entry], schema=code_schema, allow_extra=allow_extra,
                       exclude_schema=exclude_schema)
            except (ValueError, TypeError) as e2:
                _serialize_error(line_num, str(e2))
        # Fallback: error not attributable to a single entry
        _serialize_error(0, str(e))

    sys.stdout.write(result)


def main():
    subcommand, mode, code_schema, extra_fields, allow_extra, exclude_schema = _parse_args(sys.argv)

    if subcommand == "serialize":
        _serialize_main(mode, code_schema, allow_extra, exclude_schema)
        return

    # parse subcommand
    text = sys.stdin.read()

    try:
        if mode == "schema":
            schema = Schema()
            for item in parse_document_items(text):
                if isinstance(item, SchemaDirective):
                    schema._add_directive(item)
                    print(json.dumps(item.to_dict(), ensure_ascii=False))

        elif mode == "raw":
            for entry in loads_raw(text):
                print(json.dumps(entry.to_dict(), ensure_ascii=False))

        else:
            # bind mode
            result = loads(text, schema=code_schema, extra_fields=extra_fields)
            for entry in result:
                print(json.dumps(entry, ensure_ascii=False))

    except _errors.FsonlError as e:
        print(f"{e.kind}:{e.line}", file=sys.stderr)
        print(e.message, file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
