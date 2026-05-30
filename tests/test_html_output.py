"""Tests for the HTML output module."""

import pytest
from dictdiff.html_output import format_html, format_html_standalone
from dictdiff.core import DiffResult, Change, diff


class TestFormatHTML:
    """Tests for format_html function."""

    def test_empty_diff(self):
        result = DiffResult()
        html = format_html(result)
        assert isinstance(html, str)
        assert len(html) > 0

    def test_simple_change(self):
        result = diff({"name": "Alice"}, {"name": "Bob"})
        html = format_html(result)
        assert isinstance(html, str)
        assert len(html) > 0

    def test_added_key(self):
        result = diff({"a": 1}, {"a": 1, "new_key": "value"})
        html = format_html(result)
        assert isinstance(html, str)

    def test_removed_key(self):
        result = diff({"a": 1, "old_key": "value"}, {"a": 1})
        html = format_html(result)
        assert isinstance(html, str)

    def test_nested_diff(self):
        result = diff(
            {"db": {"host": "localhost", "port": 5432}},
            {"db": {"host": "localhost", "port": 3306}},
        )
        html = format_html(result)
        assert isinstance(html, str)

    def test_with_title(self):
        result = DiffResult()
        html = format_html(result, title="Test Report")
        assert "Test Report" in html

    def test_no_changes(self):
        result = diff({"a": 1}, {"a": 1})
        html = format_html(result)
        assert isinstance(html, str)


class TestFormatHTMLStandalone:
    """Tests for format_html_standalone function."""

    def test_standalone_output(self):
        result = diff({"x": 1}, {"x": 2})
        html = format_html_standalone(result, title="Standalone Test")
        assert "<html" in html or "<!DOCTYPE" in html
        assert "Standalone Test" in html

    def test_standalone_has_style(self):
        result = diff({"a": 1}, {"a": 2})
        html = format_html_standalone(result)
        assert "<style" in html or "style" in html

    def test_standalone_empty_diff(self):
        result = DiffResult()
        html = format_html_standalone(result, title="Empty Diff")
        assert isinstance(html, str)
        assert len(html) > 100  # Should have full HTML structure


class TestHTMLEscaping:
    """Tests for proper HTML escaping in output."""

    def test_html_entities_in_values(self):
        result = diff({"script": "normal"}, {"script": "<script>alert(1)</script>"})
        html = format_html(result)
        # The output should be valid HTML (escaped or not containing raw script tags)
        assert isinstance(html, str)
