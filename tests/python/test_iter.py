"""Python-specific tests — features unique to the Python implementation"""

import io
from fsonl._api import iter_entries, iter_raw
from fsonl._types import RawEntry


class TestIterEntriesFileObject:
    """iter_entries/iter_raw with file objects should produce correct results."""

    def test_file_object_works(self):
        text = '@schema x(a: string)\nx("hello")\n'
        entries = list(iter_entries(io.StringIO(text)))
        assert len(entries) == 1
        assert entries[0] == {"type": "x", "a": "hello"}

    def test_file_object_raw(self):
        entries = list(iter_raw(io.StringIO('x()\ny()\n')))
        assert len(entries) == 2
        assert isinstance(entries[0], RawEntry)
        assert entries[0].type == 'x'
        assert entries[1].type == 'y'
