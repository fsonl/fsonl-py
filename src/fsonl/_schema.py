"""Schema container class."""
from __future__ import annotations

from typing import Callable, List, Optional, Union
import os

from ._errors import SchemaError
from ._parser import _prepare_lines
from ._schema_parser import parse_schema_line, parse_schema_bare
from ._scanner import skip_ws
from ._types import SchemaDirective


class Schema:
    """Schema container. Holds @schema definitions for multiple types."""

    def __init__(self) -> None:
        self._definitions: dict = {}  # type_name → SchemaDirective

    @classmethod
    def from_string(cls, text: str) -> Schema:
        """Parse @schema syntax strings to create a Schema."""
        schema = cls()
        schema.add(text)
        return schema

    @classmethod
    def from_file(cls, path: Union[str, os.PathLike]) -> Schema:
        """Load schema from a .fsonl file. Extracts @schema lines only."""
        with open(path, encoding="utf-8", newline="") as f:
            return cls.from_fsonl(f.read())

    @classmethod
    def from_fsonl(cls, text: str) -> Schema:
        """Extract @schema lines from FSONL text to create a Schema.
        Non-schema lines (entries, comments, blank lines) are ignored."""
        schema = cls()
        for line_number, line in _prepare_lines(text):
            pos = skip_ws(line, 0)
            if pos >= len(line):
                continue

            if line[pos:pos + 7] == '@schema' and pos + 7 < len(line) and line[pos + 7] in (' ', '\t'):
                directive = parse_schema_line(line, pos + 7, line_number)
                schema._add_directive(directive)
            # All other lines (entries, comments, etc.) are silently skipped
        return schema

    def add(self, text: str) -> None:
        """Parse @schema syntax string(s) and add definitions.
        Multiple lines are supported."""
        for line_number, line in _prepare_lines(text):
            pos = skip_ws(line, 0)
            if pos >= len(line):
                continue

            # Skip comment lines
            if line[pos:pos + 2] == '//':
                continue

            # @schema prefix or bare definition
            if line[pos:pos + 7] == '@schema' and pos + 7 < len(line) and line[pos + 7] in (' ', '\t'):
                directive = parse_schema_line(line, pos + 7, line_number)
                self._add_directive(directive)
            else:
                # Try without @schema prefix: user(name: string, ...)
                directive = parse_schema_bare(line, pos, line_number)
                self._add_directive(directive)

    def _add_directive(self, directive: SchemaDirective) -> None:
        """Add a SchemaDirective to this schema. Raises SchemaError on duplicate."""
        if directive.name in self._definitions:
            raise SchemaError(directive.line, f"Duplicate schema definition for type '{directive.name}'")
        self._definitions[directive.name] = directive

    def get(self, type_name: str) -> Optional[SchemaDirective]:
        """Look up a definition by type name. Returns None if not found."""
        return self._definitions.get(type_name)

    def has(self, type_name: str) -> bool:
        """Check if a type name has a definition."""
        return type_name in self._definitions

    def type_names(self) -> List[str]:
        """Return list of all defined type names."""
        return list(self._definitions.keys())

    def define(self, fn: Callable) -> Callable:
        """Decorator to define a schema from a function signature (Python 3.10+).

        Usage:
            schema = Schema()

            @schema.define
            def user(name: str, *, email: str, role: str = "member"): ...

        Positional params: before *
        Named params: keyword-only (after *)
        Variadic: *args parameter
        """
        import sys
        if sys.version_info < (3, 10):
            raise ImportError("Schema.define decorator requires Python 3.10+")

        from ._define import _fn_to_directive
        directive = _fn_to_directive(fn)
        self._add_directive(directive)
        return fn
