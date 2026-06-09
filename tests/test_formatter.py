"""Tests for dictdiff formatter."""

from dictdiff.core import diff
from dictdiff.formatter import format_unified, _format_value


class TestFormatValue:
    """Tests for value formatting helper."""

    def test_string(self):
        assert _format_value("hello") == '"hello"'

    def test_int(self):
        assert _format_value(42) == "42"

    def test_float(self):
        assert _format_value(3.14) == "3.14"

    def test_bool(self):
        assert _format_value(True) == "True"

    def test_none(self):
        assert _format_value(None) == "null"

    def test_list(self):
        assert _format_value([1, 2]) == "[1, 2]"

    def test_dict(self):
        assert _format_value({"a": 1}) == "{'a': 1}"


class TestFormatUnified:
    """Tests for unified diff output."""

    def test_empty_diff(self):
        result = diff({"a": 1}, {"a": 1})
        assert format_unified(result) == ""

    def test_added_key(self):
        result = diff({}, {"b": 2})
        output = format_unified(result)
        assert "+b:" in output

    def test_removed_key(self):
        result = diff({"b": 2}, {})
        output = format_unified(result)
        assert "-b:" in output

    def test_changed_key(self):
        result = diff({"a": 1}, {"a": 2})
        output = format_unified(result)
        assert "-a:" in output
        assert "+a:" in output

    def test_type_changed(self):
        result = diff({"a": "42"}, {"a": 42})
        output = format_unified(result)
        assert "(str)" in output
        assert "(int)" in output

    def test_nested_change(self):
        result = diff({"a": {"b": 1}}, {"a": {"b": 2}})
        output = format_unified(result)
        assert "a.b" in output

    def test_multiple_changes(self):
        result = diff({"a": 1, "b": 2}, {"a": 99, "c": 3})
        output = format_unified(result)
        assert "-a:" in output
        assert "+a:" in output
        assert "-b:" in output
        assert "+c:" in output
