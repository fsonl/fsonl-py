"""CLI entry point: python -m fsonl parse [--raw|--allow-unknown|--schema]"""

import sys
import json

from ._parser import parse_document_items
from ._types import SchemaDirective
from ._schema import Schema
from ._api import loads, loads_raw, bind
from . import _errors


def main():
    args = sys.argv[1:]
    if not args or args[0] != "parse":
        print("Usage: fsonl parse [--raw|--allow-unknown|--schema]", file=sys.stderr)
        sys.exit(1)

    flags = set(args[1:])
    valid_flags = {"--raw", "--allow-unknown", "--schema"}
    unknown = flags - valid_flags
    if unknown:
        print(f"Error: unknown flag(s): {', '.join(unknown)}", file=sys.stderr)
        sys.exit(1)
    exclusive = flags & valid_flags
    if len(exclusive) > 1:
        print("Error: --raw, --allow-unknown, --schema are mutually exclusive", file=sys.stderr)
        sys.exit(1)

    if "--raw" in flags:
        mode = "raw"
    elif "--allow-unknown" in flags:
        mode = "allow-unknown"
    elif "--schema" in flags:
        mode = "schema"
    else:
        mode = "bind"

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
                print(json.dumps(entry, ensure_ascii=False))

        elif mode == "allow-unknown":
            # Parse raw, then try to bind each entry
            raw_result = loads_raw(text)
            file_schema = raw_result.schema

            for entry in raw_result:
                type_name = entry["type"]
                if file_schema and file_schema.has(type_name):
                    bound = bind(entry, file_schema)
                    print(json.dumps(bound, ensure_ascii=False))
                else:
                    print(json.dumps(entry, ensure_ascii=False))

        else:
            # bind mode
            result = loads(text)
            for entry in result:
                print(json.dumps(entry, ensure_ascii=False))

    except _errors.FsonlError as e:
        print(f"{e.kind}:{e.line}", file=sys.stderr)
        print(e.message, file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
