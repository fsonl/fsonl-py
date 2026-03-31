"""Python-specific tests — features unique to the Python implementation"""

from fsonl import loads_raw
from fsonl._types import RawEntry


class TestParseResultProtocol:
    """ParseResult should support __iter__, __len__, __getitem__."""

    def setup_method(self):
        self.result = loads_raw('a()\nb()\nc()\n')

    def test_len(self):
        assert len(self.result) == 3

    def test_getitem(self):
        assert self.result[0].type == 'a'
        assert self.result[1].type == 'b'
        assert self.result[2].type == 'c'

    def test_iter(self):
        types = [e.type for e in self.result]
        assert types == ['a', 'b', 'c']

    def test_iter_is_idempotent(self):
        first = list(self.result)
        second = list(self.result)
        assert first == second

    def test_negative_index(self):
        assert self.result[-1].type == 'c'

    def test_entries_are_raw_entry(self):
        assert isinstance(self.result[0], RawEntry)
