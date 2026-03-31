"""Python-specific tests — Schema.from_file and Schema.from_fsonl.

These use Python file I/O and are not expected to be ported to other languages.
"""

import os
import tempfile
import pytest
from fsonl import Schema


class TestFromFile:
    """Schema.from_file loads @schema from .fsonl files."""

    def test_from_file(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.fsonl', delete=False) as f:
            f.write('@schema x(a: string)\n@schema y(b: number)\nx("hello")\n')
            f.flush()
            path = f.name
        try:
            s = Schema.from_file(path)
            assert s.type_names() == ['x', 'y']
        finally:
            os.unlink(path)

    def test_from_file_ignores_entries(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.fsonl', delete=False) as f:
            f.write('x("hello")\n@schema x(a: string)\n')
            f.flush()
            path = f.name
        try:
            s = Schema.from_file(path)
            assert s.has('x')
        finally:
            os.unlink(path)


class TestSchemaFromFsonl:
    """Schema.from_fsonl() should extract @schema lines and ignore entries."""

    def test_extracts_schema_lines(self):
        text = '@schema x(a: string)\n@schema y(b: number)\nx("hello")\n'
        schema = Schema.from_fsonl(text)
        assert schema.has('x')
        assert schema.has('y')

    def test_ignores_entry_lines(self):
        text = 'x("hello")\n@schema x(a: string)\ny(42)\n'
        schema = Schema.from_fsonl(text)
        assert schema.has('x')
        assert not schema.has('y')

    def test_ignores_comment_lines(self):
        text = '// a comment\n@schema z(n: number)\n// another\n'
        schema = Schema.from_fsonl(text)
        assert schema.has('z')
        assert schema.type_names() == ['z']

    def test_ignores_blank_lines(self):
        text = '\n@schema a(v: bool)\n\n'
        schema = Schema.from_fsonl(text)
        assert schema.has('a')

    def test_empty_fsonl_returns_empty_schema(self):
        schema = Schema.from_fsonl('')
        assert schema.type_names() == []
