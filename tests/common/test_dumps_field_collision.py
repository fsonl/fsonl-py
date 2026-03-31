"""Common API tests — all language implementations should have equivalent tests.

Covers: serializer correctly distinguishes bound entries from raw entries
when schema fields are named 'positional' or 'named'.
"""

import pytest
from fsonl import dumps, loads, Schema, RawEntry


class TestBoundEntryWithCollisionFieldNames:
    """A plain dict (bound entry) must always be treated as bound, even if it has
    keys 'positional' or 'named'.  Only a RawEntry-typed object should be treated
    as raw.

    Some language implementations detect raw entries by checking for the presence
    of 'positional'/'named' keys in a plain dict.  That is incorrect; the Python
    implementation correctly uses isinstance(entry, RawEntry) and should pass all
    tests below.  Tests are marked with comments where other implementations are
    known to fail.
    """

    # ------------------------------------------------------------------
    # Test 1: schema field named "positional"
    # ------------------------------------------------------------------
    def test_field_named_positional_serializes_as_bound(self):
        """Bound entry with a field literally named 'positional' should serialize
        using the schema (named arg), not be misidentified as a raw entry.

        Known issue in implementations that use `"positional" in entry` heuristic.
        """
        schema = Schema.from_string('@schema T(--positional: string)')
        entry = {"type": "T", "positional": "some_value"}
        result = dumps(entry, schema=schema, exclude_schema=True)
        # Should produce T(positional="some_value") — a named arg
        assert result == 'T(positional="some_value")\n'

    # ------------------------------------------------------------------
    # Test 2: schema field named "named"
    # ------------------------------------------------------------------
    def test_field_named_named_serializes_as_bound(self):
        """Bound entry with a field literally named 'named' should serialize
        using the schema (named arg), not be misidentified as a raw entry.

        Known issue in implementations that use `"named" in entry` heuristic.
        """
        schema = Schema.from_string('@schema T(--named: string)')
        entry = {"type": "T", "named": "some_value"}
        result = dumps(entry, schema=schema, exclude_schema=True)
        # Should produce T(named="some_value")
        assert result == 'T(named="some_value")\n'

    # ------------------------------------------------------------------
    # Test 3: schema with BOTH "positional" and "named" fields
    # ------------------------------------------------------------------
    def test_both_collision_fields_serialize_as_bound(self):
        """Bound entry with both 'positional' and 'named' fields should still
        serialize as a bound entry using the schema.

        Known issue in implementations that treat {positional, named} dict as raw.
        """
        schema = Schema.from_string('@schema T(--positional: string, --named: string)')
        entry = {"type": "T", "positional": "p_val", "named": "n_val"}
        result = dumps(entry, schema=schema, exclude_schema=True)
        assert result == 'T(positional="p_val", named="n_val")\n'

    # ------------------------------------------------------------------
    # Test 4: schema field "positional" as array type (positional param)
    # ------------------------------------------------------------------
    def test_field_named_positional_array_as_positional_param(self):
        """Bound entry where 'positional' is a positional (non-named) schema param
        of array type.  Should serialize the value as a positional arg, not
        misinterpret the array as a raw entry's positional list.

        Known issue in implementations that use `"positional" in entry` heuristic.
        """
        schema = Schema.from_string('@schema T(positional: number[])')
        entry = {"type": "T", "positional": [1, 2]}
        result = dumps(entry, schema=schema, exclude_schema=True)
        # 'positional' is a positional schema param whose value is [1, 2]
        assert result == 'T([1, 2])\n'

    # ------------------------------------------------------------------
    # Test 5: round-trip with "positional" field name
    # ------------------------------------------------------------------
    def test_round_trip_with_positional_field_name(self):
        """loads → dumps → loads should produce the same entry when the schema
        has a field named 'positional'.
        """
        schema = Schema.from_string('@schema T(--positional: string)')
        original_text = 'T(positional="hello")\n'
        parsed = loads(original_text, schema=schema)
        assert parsed.entries[0] == {"type": "T", "positional": "hello"}

        serialized = dumps(parsed.entries[0], schema=schema, exclude_schema=True)
        re_parsed = loads(serialized, schema=schema)
        assert re_parsed.entries[0] == parsed.entries[0]

    # ------------------------------------------------------------------
    # Test 6: contrast — actual RawEntry still works correctly
    # ------------------------------------------------------------------
    def test_actual_raw_entry_still_serializes_as_raw(self):
        """A RawEntry object (not a plain dict) with positional args and named args
        must still be serialized as a raw entry regardless of field names.
        """
        raw = RawEntry(type="T", positional=[1, 2], named={"x": "val"})
        result = dumps(raw)
        assert result == 'T(1, 2, x="val")\n'

    def test_raw_entry_with_collision_names_in_named(self):
        """A RawEntry whose named dict has keys 'positional' and 'named' must
        still serialize as a raw entry (the RawEntry type is the discriminator,
        not the key names).
        """
        raw = RawEntry(type="T", positional=[], named={"positional": "p", "named": "n"})
        result = dumps(raw)
        assert result == 'T(positional="p", named="n")\n'
