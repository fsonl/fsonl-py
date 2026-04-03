"""Python-specific tests — Writer context manager and pathlib support."""

import pytest
from fsonl import Schema, RawEntry, loads

# Will fail until Writer is implemented
from fsonl import Writer


class TestWriterContextManager:
    """with statement support."""

    def test_basic_with(self, tmp_path):
        path = tmp_path / "test.fsonl"
        schema = Schema.from_string('@schema x(a: string)')
        with Writer(path, schema=schema) as w:
            w.write({"type": "x", "a": "hello"})
        content = path.read_text()
        assert content == '@schema x(a: string)\nx("hello")\n'

    def test_with_flushes_on_exit(self, tmp_path):
        path = tmp_path / "test.fsonl"
        with Writer(path) as w:
            w.write({"type": "x", "a": "val"})
        assert path.exists()
        assert 'x(a="val")' in path.read_text()

    def test_with_closes_on_exception(self, tmp_path):
        path = tmp_path / "test.fsonl"
        schema = Schema.from_string('@schema x(a: string)')
        try:
            with Writer(path, schema=schema) as w:
                w.write({"type": "x", "a": "before"})
                raise RuntimeError("boom")
        except RuntimeError:
            pass
        content = path.read_text()
        assert 'x("before")' in content


class TestWriterPathlib:
    """pathlib.Path and str path support."""

    def test_str_path(self, tmp_path):
        path = str(tmp_path / "test.fsonl")
        with Writer(path) as w:
            w.write({"type": "x", "v": 1})
        with open(path) as f:
            assert 'x(v=1)' in f.read()

    def test_pathlib_path(self, tmp_path):
        path = tmp_path / "test.fsonl"
        with Writer(path) as w:
            w.write({"type": "x", "v": 1})
        assert 'x(v=1)' in path.read_text()
