"""Stateful Writer for append-friendly FSONL serialization."""

import os
from typing import Optional, Union

from ._schema import Schema
from ._serializer import dumps
from ._types import RawEntry


class Writer:
    """Append-friendly FSONL writer.

    Opens a file for writing/appending. If the file is new (or empty),
    writes the schema header first. If the file already has content,
    appends entries without duplicating the header.

    Usage:
        with Writer("log.fsonl", schema=s) as w:
            w.write({"type": "x", "a": "hello"})
    """

    def __init__(
        self,
        path: Union[str, os.PathLike],
        *,
        schema: Optional[Schema] = None,
    ) -> None:
        self._path = path
        self._schema = schema
        self._fp = None
        self._header_written = False
        self._open()

    def _open(self) -> None:
        is_new = not os.path.exists(self._path) or os.path.getsize(self._path) == 0
        if is_new:
            self._fp = open(self._path, "w", encoding="utf-8", newline="")
            if self._schema is not None:
                header = dumps([], schema=self._schema)
                if header:
                    self._fp.write(header)
                    self._header_written = True
        else:
            self._fp = open(self._path, "a", encoding="utf-8", newline="")
            self._header_written = True  # assume existing file has header

    def write(self, entry: Union[dict, RawEntry]) -> None:
        """Write a single entry to the file."""
        text = dumps([entry], schema=self._schema, exclude_schema=True)
        self._fp.write(text)

    def close(self) -> None:
        """Flush and close the underlying file."""
        if self._fp is not None:
            self._fp.close()
            self._fp = None

    def __enter__(self) -> "Writer":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()
