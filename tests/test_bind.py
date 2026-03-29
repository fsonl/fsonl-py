"""bind() error type tests: no-schema case should raise BindError."""

import pytest
from fsonl import bind, Schema
from fsonl._errors import BindError


class TestBindNoSchema:
    """bind() with missing schema should raise BindError, not SchemaError."""

    def test_no_schema_for_type(self):
        entry = {"type": "unknown", "positional": [], "named": {}, "_line": 7}
        schema = Schema()
        with pytest.raises(BindError, match="No schema for type 'unknown'"):
            bind(entry, schema)

    def test_error_preserves_line(self):
        entry = {"type": "missing", "positional": [], "named": {}, "_line": 42}
        schema = Schema()
        with pytest.raises(BindError) as exc_info:
            bind(entry, schema)
        assert exc_info.value.line == 42
        assert exc_info.value.kind == "bind_error"
