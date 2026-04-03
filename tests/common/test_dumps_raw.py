"""Common API tests — all language implementations should have equivalent tests.

Covers: dumps() with RawEntry — validation of type names and named keys.
These test error messages and exception types, which E2E only checks exit code.
Valid RawEntry serialization is covered by E2E serialize/raw.toml.
"""

import pytest
from fsonl import dumps, RawEntry


class TestFormatRawRejectsInvalid:
    def test_invalid_type_name_hyphen(self):
        with pytest.raises(ValueError, match="bad-name"):
            dumps([RawEntry("bad-name", [], {})])

    def test_invalid_type_name_space(self):
        with pytest.raises(ValueError, match="bad name"):
            dumps([RawEntry("bad name", [], {})])

    def test_invalid_type_name_digit_start(self):
        with pytest.raises(ValueError, match="123"):
            dumps([RawEntry("123", [], {})])

    def test_invalid_named_key_hyphen(self):
        with pytest.raises(ValueError, match="dry-run"):
            dumps([RawEntry("ok", [], {"dry-run": True})])

    def test_reserved_type_key(self):
        with pytest.raises(ValueError, match="type"):
            dumps([RawEntry("ok", [], {"type": "x"})])
