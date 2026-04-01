"""Tests for PR #1 review comment fixes: type annotations, docstrings, usage text."""
import inspect
import typing

from fsonl._api import loads_raw, iter_raw
from fsonl._types import RawEntry


def test_loads_raw_entries_annotation_is_rawentry():
    """loads_raw should annotate entries as List[RawEntry], not List[Dict]."""
    source = inspect.getsource(loads_raw)
    assert "List[Dict[str, Any]]" not in source
    assert "List[RawEntry]" in source


def test_loads_raw_docstring_mentions_rawentry():
    """loads_raw docstring should reference RawEntry, not raw entry dicts."""
    doc = loads_raw.__doc__
    assert doc is not None
    assert "raw entry dict" not in doc
    assert "RawEntry" in doc


def test_iter_raw_return_type_is_rawentry():
    """iter_raw return annotation should be Iterator[RawEntry]."""
    hints = typing.get_type_hints(iter_raw)
    ret = hints["return"]
    assert ret is not typing.Iterator[typing.Dict[str, typing.Any]]
    # Check it's Iterator[RawEntry]
    args = typing.get_args(ret)
    assert args == (RawEntry,)


def test_iter_raw_docstring_mentions_rawentry():
    """iter_raw docstring should reference RawEntry, not raw entries."""
    doc = iter_raw.__doc__
    assert doc is not None
    assert "RawEntry" in doc


def test_cli_usage_mentions_extra_fields():
    """CLI module docstring and usage text should mention --extra-fields."""
    import fsonl.__main__ as cli_mod
    source = inspect.getsource(cli_mod)
    assert "--extra-fields" in source.split("def ")[0]  # in module docstring area
    assert cli_mod.__doc__ is not None
    assert "--extra-fields" in cli_mod.__doc__
