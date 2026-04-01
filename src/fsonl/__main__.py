"""CLI entry point: python -m fsonl parse [--raw|--schema] [--define '...']"""

import sys
import json

from ._parser import parse_document_items
from ._types import SchemaDirective
from ._schema import Schema
from ._types import ExtraFieldPolicy
from ._api import loads, loads_raw
from . import _errors

_EXTRA_FIELD_VALUES = {p.value: p for p in ExtraFieldPolicy}


def _parse_args(argv):
    """Parse CLI arguments, extracting mode flags and --define values."""
    args = argv[1:]
    if not args or args[0] != "parse":
        print("Usage: fsonl parse [--raw|--schema] [--define '...']", file=sys.stderr)
        sys.exit(1)

    mode_flags = set()
    defines = []
    extra_fields = ExtraFieldPolicy.ERROR
    i = 1
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
                print(f"Error: --extra-fields must be one of: error, preserve, strip", file=sys.stderr)
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

    # Build code schema from --define values
    code_schema = None
    if defines:
        code_schema = Schema()
        for d in defines:
            code_schema.add(d)

    return mode, code_schema, extra_fields


def main():
    mode, code_schema, extra_fields = _parse_args(sys.argv)

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
