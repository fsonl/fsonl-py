from __future__ import annotations

import enum
from dataclasses import dataclass
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
