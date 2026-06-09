"""Tests for dictdiff CLI."""

import json

import pytest
from click.testing import CliRunner

from dictdiff.cli import main


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def json_old(tmp_path):
    p = tmp_path / "old.json"
    p.write_text(json.dumps({"a": 1, "b": 2, "c": 3}))
    return str(p)


@pytest.fixture
def json_new(tmp_path):
    p = tmp_path / "new.json"
    p.write_text(json.dumps({"a": 1, "b": 99, "d": 4}))
    return str(p)


@pytest.fixture
def json_identical(tmp_path):
    p = tmp_path / "same.json"
    p.write_text(json.dumps({"a": 1, "b": 2}))
    return str(p)


class TestCLIBasic:
    """Tests for basic CLI functionality."""

    def test_diff_with_changes(self, runner, json_old, json_new):
        result = runner.invoke(main, [json_old, json_new])
        assert result.exit_code == 1  # differences found

    def test_diff_identical(self, runner, json_identical):
        result = runner.invoke(main, [json_identical, json_identical])
        assert result.exit_code == 0  # no differences

    def test_file_not_found(self, runner):
        result = runner.invoke(main, ["nonexistent.json", "also_nonexistent.json"])
        assert result.exit_code == 2

    def test_quiet_mode_no_diff(self, runner, json_identical):
        result = runner.invoke(main, ["-q", json_identical, json_identical])
        assert result.exit_code == 0
        assert result.output == ""

    def test_quiet_mode_with_diff(self, runner, json_old, json_new):
        result = runner.invoke(main, ["-q", json_old, json_new])
        assert result.exit_code == 1
        assert result.output == ""


class TestCLIPatch:
    """Tests for --patch flag."""

    def test_patch_output(self, runner, json_old, json_new):
        result = runner.invoke(main, ["--patch", json_old, json_new])
        assert result.exit_code == 1
        patch_data = json.loads(result.output)
        assert isinstance(patch_data, list)
        assert any(op["op"] in ("add", "remove", "replace") for op in patch_data)

    def test_patch_identical(self, runner, json_identical):
        result = runner.invoke(main, ["--patch", json_identical, json_identical])
        assert result.exit_code == 0
        patch_data = json.loads(result.output)
        assert patch_data == []


class TestCLIFormats:
    """Tests for --format flag."""

    def test_json_format(self, runner, json_old, json_new):
        result = runner.invoke(main, ["--format", "json", json_old, json_new])
        assert result.exit_code == 1
        data = json.loads(result.output)
        assert "added" in data or "removed" in data or "changed" in data

    def test_unified_format(self, runner, json_old, json_new):
        result = runner.invoke(main, ["--format", "unified", json_old, json_new])
        assert result.exit_code == 1
        assert "+" in result.output or "-" in result.output

    def test_tree_format(self, runner, json_old, json_new):
        result = runner.invoke(main, ["--format", "tree", json_old, json_new])
        assert result.exit_code == 1

    def test_table_format(self, runner, json_old, json_new):
        result = runner.invoke(main, ["--format", "table", json_old, json_new])
        assert result.exit_code == 1


class TestCLIIgnore:
    """Tests for --ignore flag."""

    def test_ignore_changed_key(self, runner, json_old, json_new):
        result = runner.invoke(main, ["--ignore", "b", json_old, json_new])
        # b is changed, d is added, c is removed — still differences
        assert result.exit_code == 1

    def test_ignore_all_changed_keys(self, runner, json_old, json_new):
        result = runner.invoke(
            main,
            ["--ignore", "b", "--ignore", "c", "--ignore", "d", json_old, json_new],
        )
        assert result.exit_code == 0


class TestCLIStdin:
    """Tests for stdin input with '-'."""

    def test_stdin_old(self, runner, json_new):
        old_data = json.dumps({"a": 1, "b": 2, "c": 3})
        result = runner.invoke(main, ["-", json_new], input=old_data)
        assert result.exit_code == 1

    def test_stdin_both_not_supported(self, runner):
        result = runner.invoke(main, ["-", "-"])
        # Second "-" also reads from stdin, which would need to be provided separately
        # This is a known limitation — at least one file must be a real file
        assert result.exit_code != 0 or "Error" in result.output


class TestCLIVersion:
    """Tests for --version flag."""

    def test_version(self, runner):
        result = runner.invoke(main, ["--version"])
        assert "0.2.0" in result.output
