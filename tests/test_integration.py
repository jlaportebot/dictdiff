"""Integration tests for dictdiff — end-to-end workflows."""

import json
import os
import tempfile
import pytest

from dictdiff.core import diff, DiffResult, Change
from dictdiff.patch import generate_patch, apply_patch
from dictdiff.convenience import diff_files, diff_strings
from dictdiff.ignore import IgnoreMatcher, filter_dict
from dictdiff.paths import extract_path, list_paths, path_exists, set_path, remove_path
from dictdiff.loader import load_file, load_string, detect_format
from dictdiff.merge3 import merge3
from dictdiff.schema import (
    validate,
    StringType,
    IntType,
    DictType,
    ListType,
    EnumType,
)
from dictdiff.html_output import format_html, format_html_standalone


class TestDiffToPatchRoundtrip:
    """Test that diff → patch → apply produces the new value."""

    def test_simple_dict_patch(self):
        old = {"name": "Alice", "age": 30, "city": "NYC"}
        new = {"name": "Bob", "age": 31, "city": "NYC", "email": "bob@example.com"}
        result = diff(old, new)
        patch = generate_patch(result)
        restored = apply_patch(old, patch)
        assert restored == new

    def test_nested_dict_patch(self):
        old = {"db": {"host": "localhost", "port": 5432}}
        new = {"db": {"host": "remote", "port": 3306}}
        result = diff(old, new)
        patch = generate_patch(result)
        restored = apply_patch(old, patch)
        assert restored == new

    def test_added_keys_patch(self):
        old = {"a": 1}
        new = {"a": 1, "b": 2, "c": 3}
        result = diff(old, new)
        patch = generate_patch(result)
        restored = apply_patch(old, patch)
        assert restored == new

    def test_removed_keys_patch(self):
        old = {"a": 1, "b": 2, "c": 3}
        new = {"a": 1}
        result = diff(old, new)
        patch = generate_patch(result)
        restored = apply_patch(old, patch)
        assert restored == new

    def test_type_change_patch(self):
        old = {"count": "5"}
        new = {"count": 5}
        result = diff(old, new)
        patch = generate_patch(result)
        restored = apply_patch(old, patch)
        assert restored == new

    def test_deeply_nested_patch(self):
        old = {"a": {"b": {"c": {"d": 1}}}}
        new = {"a": {"b": {"c": {"d": 2, "e": 3}}}}
        result = diff(old, new)
        patch = generate_patch(result)
        restored = apply_patch(old, patch)
        assert restored == new


class TestDiffWithIgnore:
    """Test diff workflow with ignore patterns."""

    def test_diff_ignoring_timestamps(self):
        old = {
            "name": "Alice",
            "updated_at": "2024-01-01",
            "created_at": "2024-01-01",
        }
        new = {
            "name": "Bob",
            "updated_at": "2024-06-01",
            "created_at": "2024-01-01",
        }
        matcher = IgnoreMatcher()
        matcher.add_glob("*_at")

        filtered_old = filter_dict(old, matcher)
        filtered_new = filter_dict(new, matcher)

        result = diff(filtered_old, filtered_new)
        assert "name" in result.changed
        assert "updated_at" not in result.changed

    def test_diff_ignoring_password(self):
        old = {"user": "alice", "password": "old_pass"}
        new = {"user": "alice", "password": "new_pass"}

        matcher = IgnoreMatcher()
        matcher.add_exact("password")

        filtered_old = filter_dict(old, matcher)
        filtered_new = filter_dict(new, matcher)

        result = diff(filtered_old, filtered_new)
        assert result.is_empty  # Only password changed, and we ignored it


class TestDiffWithPathFiltering:
    """Test diff with path extraction."""

    def test_diff_at_subpath(self):
        old = {"config": {"db": {"host": "localhost"}}, "version": "1.0"}
        new = {"config": {"db": {"host": "remote"}}, "version": "2.0"}

        # Extract just the db subpath
        old_db = extract_path(old, "config.db")
        new_db = extract_path(new, "config.db")

        result = diff(old_db, new_db)
        assert "host" in result.changed
        # version is not in the subpath, so not in the diff


class TestDiffWithSchemaValidation:
    """Test diff with schema validation before diffing."""

    def test_valid_data_then_diff(self):
        schema = DictType(
            required_keys={"name": StringType(), "age": IntType()},
        )

        old = {"name": "Alice", "age": 30}
        new = {"name": "Bob", "age": 31}

        # Validate first
        assert validate(old, schema).is_valid
        assert validate(new, schema).is_valid

        # Then diff
        result = diff(old, new)
        assert "name" in result.changed
        assert "age" in result.changed


class TestDiffFileWorkflows:
    """Test diff_files and diff_strings convenience functions."""

    def test_diff_strings_json(self):
        old_json = '{"name": "Alice", "age": 30}'
        new_json = '{"name": "Bob", "age": 31}'
        result = diff_strings(old_json, new_json, format="json")
        assert isinstance(result, DiffResult)
        assert not result.is_empty

    def test_diff_files_json(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f1:
            json.dump({"x": 1}, f1)
            f1.flush()
            old_path = f1.name
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f2:
            json.dump({"x": 2}, f2)
            f2.flush()
            new_path = f2.name
        try:
            result = diff_files(old_path, new_path)
            assert isinstance(result, DiffResult)
            assert not result.is_empty
        finally:
            os.unlink(old_path)
            os.unlink(new_path)


class TestMerge3Workflows:
    """End-to-end three-way merge workflows."""

    def test_config_merge(self):
        """Realistic config merge scenario."""
        base = {
            "database": {"host": "localhost", "port": 5432, "name": "mydb"},
            "logging": {"level": "INFO", "file": "/var/log/app.log"},
            "features": {"search": True, "auth": True},
        }
        ours = {
            "database": {"host": "prod-server", "port": 5432, "name": "mydb"},
            "logging": {"level": "INFO", "file": "/var/log/app.log"},
            "features": {"search": True, "auth": True, "cache": True},
        }
        theirs = {
            "database": {"host": "localhost", "port": 5432, "name": "mydb"},
            "logging": {"level": "WARNING", "file": "/var/log/app.log"},
            "features": {"search": True, "auth": True, "metrics": True},
        }

        result = merge3(base, ours, theirs)
        assert not result.has_conflicts
        # ours changed host, theirs changed logging level
        assert result.merged["database"]["host"] == "prod-server"
        assert result.merged["logging"]["level"] == "WARNING"
        # both added different features — no conflict
        assert result.merged["features"].get("cache") is True
        assert result.merged["features"].get("metrics") is True


class TestHTMLReportWorkflow:
    """End-to-end HTML report generation."""

    def test_generate_html_report(self):
        old = {"config": {"host": "localhost", "port": 5432}}
        new = {"config": {"host": "remote", "port": 3306, "ssl": True}}
        result = diff(old, new)
        html = format_html_standalone(result, title="Config Diff Report")
        assert "<html" in html
        assert "Config Diff Report" in html
        assert len(html) > 500


class TestListPathsAndExtract:
    """Test path listing and extraction together."""

    def test_list_then_extract(self):
        data = {
            "config": {
                "db": {"host": "localhost", "port": 5432},
                "cache": {"enabled": True},
            },
            "version": "1.0",
        }
        paths = list_paths(data)
        assert "config.db.host" in paths
        assert "config.db.port" in paths
        assert "config.cache.enabled" in paths
        assert "version" in paths

        # Now extract each leaf
        for p in paths:
            assert path_exists(data, p)
            val = extract_path(data, p)
            assert val is not None


class TestSetPathAndDiff:
    """Test set_path followed by diff."""

    def test_set_value_then_diff(self):
        original = {"a": 1, "b": 2}
        modified = {"a": 1, "b": 2}
        set_path(modified, "b", 20)
        set_path(modified, "c", 3)

        result = diff(original, modified)
        assert "b" in result.changed
        assert "c" in result.added


class TestRemovePathAndDiff:
    """Test remove_path followed by diff."""

    def test_remove_key_then_diff(self):
        original = {"a": 1, "b": 2, "c": 3}
        modified = {"a": 1, "b": 2, "c": 3}
        remove_path(modified, "c")

        result = diff(original, modified)
        assert "c" in result.removed
