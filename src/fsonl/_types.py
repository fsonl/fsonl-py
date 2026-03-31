from __future__ import annotations

import enum
from dataclasses import dataclass, field
from typing import Any, Iterator, List, Optional


class _OmitType:
    """Sentinel for optional parameters without a default value."""
    _instance = None

    def __new__(cls) -> _OmitType:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __repr__(self) -> str:
        return "OMIT"


OMIT: Any = _OmitType()


class ExtraFieldPolicy(enum.Enum):
    """Policy for handling undeclared fields in typed objects."""
    ERROR = "error"
    PRESERVE = "preserve"
    STRIP = "strip"


@dataclass
class SchemaParam:
    name: str
    kind: str
    schema_type: Any
    optional: bool = False
    variadic: bool = False
    has_default: bool = False
    default: Any = None

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "kind": self.kind,
            "type": schema_type_to_json(self.schema_type),
            "optional": self.optional,
            "variadic": self.variadic,
            "has_default": self.has_default,
            "default": self.default,
        }


@dataclass
class SchemaDirective:
    name: str
    params: List[SchemaParam]
    line: int

    def to_dict(self) -> dict:
        return {
            "@schema": self.name,
            "params": [p.to_dict() for p in self.params],
        }


def schema_type_to_json(st: Any) -> Any:
    """Convert internal schema type representation to JSON output format."""
    if isinstance(st, str):
        return st
    if isinstance(st, dict):
        kind = st.get("kind")
        if kind == "array":
            return {"array": schema_type_to_json(st["element"])}
        elif kind == "union":
            return {"union": [schema_type_to_json(t) for t in st["types"]]}
        elif kind == "object":
            return {"object": [
                {
                    "name": f["name"],
                    "type": schema_type_to_json(f["type"]),
                    "optional": f["optional"],
                }
                for f in st["fields"]
            ]}
    return st


@dataclass(frozen=True)
class RawEntry:
    """A raw parsed entry (Stage 1 AST)."""
    type: str
    positional: list
    named: dict
    _line: int = field(default=0, repr=False, compare=False)

    def __getitem__(self, key: str) -> Any:
        if key == "type":
            return self.type
        if key == "positional":
            return self.positional
        if key == "named":
            return self.named
        if key == "_line":
            return self._line
        raise KeyError(key)

    def __contains__(self, key: object) -> bool:
        return key in ("type", "positional", "named")

    def get(self, key: str, default: Any = None) -> Any:
        try:
            return self[key]
        except KeyError:
            return default

    def keys(self) -> tuple:
        return ("type", "positional", "named")

    def items(self) -> Iterator[tuple]:
        yield ("type", self.type)
        yield ("positional", self.positional)
        yield ("named", self.named)

    def to_dict(self) -> dict:
        return {"type": self.type, "positional": list(self.positional), "named": dict(self.named)}


class ParseResult:
    def __init__(self, entries: List[Any], schema: Optional[Any] = None) -> None:
        self.entries = entries
        self.schema = schema

    def __iter__(self) -> Iterator[Any]:
        return iter(self.entries)

    def __len__(self) -> int:
        return len(self.entries)

    def __getitem__(self, index: int) -> Any:
        return self.entries[index]
