"""Python-specific tests — features unique to the Python implementation"""

import io
import os
import tempfile
from fsonl import dump, Schema


class TestDump:
    """dump() should write serialized FSONL to a file object."""

    def test_dump_single_entry(self):
        buf = io.StringIO()
        dump([{"type": "x", "v": 1}], buf)
        assert buf.getvalue() == 'x(v=1)\n'

    def test_dump_with_schema(self):
        schema = Schema.from_string('@schema x(a: string)')
        buf = io.StringIO()
        dump([{"type": "x", "a": "hi"}], buf, schema=schema)
        assert buf.getvalue() == '@schema x(a: string)\nx("hi")\n'

    def test_dump_with_exclude_schema(self):
        schema = Schema.from_string('@schema x(a: string)')
        buf = io.StringIO()
        dump([{"type": "x", "a": "hi"}], buf, schema=schema, exclude_schema=True)
        assert buf.getvalue() == 'x("hi")\n'

    def test_dump_list_of_entries(self):
        schema = Schema.from_string('@schema x(a: string)')
        buf = io.StringIO()
        entries = [{"type": "x", "a": "one"}, {"type": "x", "a": "two"}]
        dump(entries, buf, schema=schema, exclude_schema=True)
        assert buf.getvalue() == 'x("one")\nx("two")\n'

    def test_dump_writes_to_real_file(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.fsonl', delete=False) as f:
            path = f.name
            dump([{"type": "ev", "n": 7}], f)
        try:
            with open(path) as f:
                assert f.read() == 'ev(n=7)\n'
        finally:
            os.unlink(path)
