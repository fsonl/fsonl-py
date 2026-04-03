"""Common API tests — all language implementations should have equivalent tests.

Covers: Writer class — stateful append-friendly serialization.
"""

import pytest
from fsonl import loads, Schema, RawEntry


# Writer is not yet exported; import will fail until implemented.
# Each test file documents the expected API contract.
from fsonl import Writer


class TestWriterNewFile:
    """Writer on a new (nonexistent) file writes schema header then entries."""

    def test_single_entry(self, tmp_path):
        path = tmp_path / "test.fsonl"
        schema = Schema.from_string('@schema x(a: string)')
        w = Writer(path, schema=schema)
        w.write({"type": "x", "a": "hello"})
        w.close()
        content = path.read_text()
        assert content == '@schema x(a: string)\nx("hello")\n'

    def test_multiple_writes(self, tmp_path):
        path = tmp_path / "test.fsonl"
        schema = Schema.from_string('@schema x(a: string)')
        w = Writer(path, schema=schema)
        w.write({"type": "x", "a": "one"})
        w.write({"type": "x", "a": "two"})
        w.close()
        content = path.read_text()
        assert content == '@schema x(a: string)\nx("one")\nx("two")\n'

    def test_schemaless(self, tmp_path):
        path = tmp_path / "test.fsonl"
        w = Writer(path)
        w.write({"type": "x", "a": "hello"})
        w.close()
        content = path.read_text()
        assert content == 'x(a="hello")\n'

    def test_raw_entry(self, tmp_path):
        path = tmp_path / "test.fsonl"
        w = Writer(path)
        w.write(RawEntry("x", [1, "hi"], {"k": True}))
        w.close()
        content = path.read_text()
        assert content == 'x(1, "hi", k=true)\n'


class TestWriterAppend:
    """Writer on an existing file appends without duplicating schema header."""

    def test_append_skips_header(self, tmp_path):
        path = tmp_path / "test.fsonl"
        schema = Schema.from_string('@schema x(a: string)')
        # First write: creates file with header
        w1 = Writer(path, schema=schema)
        w1.write({"type": "x", "a": "first"})
        w1.close()
        # Second write: appends data only
        w2 = Writer(path, schema=schema)
        w2.write({"type": "x", "a": "second"})
        w2.close()
        content = path.read_text()
        assert content.count('@schema') == 1
        assert 'x("first")' in content
        assert 'x("second")' in content

    def test_append_to_nonempty_file(self, tmp_path):
        path = tmp_path / "test.fsonl"
        path.write_text('@schema x(a: string)\nx("existing")\n')
        schema = Schema.from_string('@schema x(a: string)')
        w = Writer(path, schema=schema)
        w.write({"type": "x", "a": "appended"})
        w.close()
        content = path.read_text()
        assert content.count('@schema') == 1
        assert 'x("existing")' in content
        assert 'x("appended")' in content

    def test_append_schemaless(self, tmp_path):
        path = tmp_path / "test.fsonl"
        path.write_text('x(a="one")\n')
        w = Writer(path)
        w.write({"type": "x", "a": "two"})
        w.close()
        content = path.read_text()
        assert content == 'x(a="one")\nx(a="two")\n'


class TestWriterRoundTrip:
    """File written by Writer should be loadable via loads()."""

    def test_written_file_is_loadable(self, tmp_path):
        path = tmp_path / "test.fsonl"
        schema = Schema.from_string('@schema x(a: string, --b: number)')
        w = Writer(path, schema=schema)
        w.write({"type": "x", "a": "hello", "b": 42})
        w.write({"type": "x", "a": "world", "b": 99})
        w.close()
        result = loads(path.read_text(), schema=schema)
        assert result.entries[0] == {"type": "x", "a": "hello", "b": 42}
        assert result.entries[1] == {"type": "x", "a": "world", "b": 99}

    def test_appended_file_is_loadable(self, tmp_path):
        path = tmp_path / "test.fsonl"
        schema = Schema.from_string('@schema x(a: string)')
        w1 = Writer(path, schema=schema)
        w1.write({"type": "x", "a": "first"})
        w1.close()
        w2 = Writer(path, schema=schema)
        w2.write({"type": "x", "a": "second"})
        w2.close()
        result = loads(path.read_text(), schema=schema)
        assert len(result.entries) == 2
        assert result.entries[0]["a"] == "first"
        assert result.entries[1]["a"] == "second"


class TestWriterEmptyClose:
    """Writer opened and closed without writes."""

    def test_new_file_with_schema_writes_header_only(self, tmp_path):
        path = tmp_path / "test.fsonl"
        schema = Schema.from_string('@schema x(a: string)')
        w = Writer(path, schema=schema)
        w.close()
        content = path.read_text()
        assert content == '@schema x(a: string)\n'

    def test_new_file_without_schema_creates_empty(self, tmp_path):
        path = tmp_path / "test.fsonl"
        w = Writer(path)
        w.close()
        assert not path.exists() or path.read_text() == ''
