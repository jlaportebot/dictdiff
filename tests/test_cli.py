"""Tests for dictdiff CLI."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from dictdiff.cli import main


def _write_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, indent=2))


class TestCLI:
    def test_identical_files(self, tmp_path: Path, capsys):
        old = tmp_path / "old.json"
        new = tmp_path / "new.json"
        _write_json(old, {"a": 1})
        _write_json(new, {"a": 1})
        rc = main([str(old), str(new)])
        assert rc == 0
        assert "No differences" in capsys.readouterr().out

    def test_different_files(self, tmp_path: Path, capsys):
        old = tmp_path / "old.json"
        new = tmp_path / "new.json"
        _write_json(old, {"a": 1})
        _write_json(new, {"a": 2})
        rc = main([str(old), str(new)])
        assert rc == 1
        assert "a" in capsys.readouterr().out

    def test_flat_format(self, tmp_path: Path, capsys):
        old = tmp_path / "old.json"
        new = tmp_path / "new.json"
        _write_json(old, {"a": 1, "b": 2})
        _write_json(new, {"a": 1, "b": 3})
        rc = main([str(old), str(new), "-f", "flat"])
        assert rc == 1

    def test_json_format(self, tmp_path: Path, capsys):
        old = tmp_path / "old.json"
        new = tmp_path / "new.json"
        _write_json(old, {"a": 1})
        _write_json(new, {"a": 2})
        rc = main([str(old), str(new), "-f", "json"])
        assert rc == 1
        output = capsys.readouterr().out
        parsed = json.loads(output)
        assert isinstance(parsed, list)
        assert parsed[0]["kind"] == "value_changed"
        assert parsed[0]["path"] == "a"

    def test_quiet_mode_identical(self, tmp_path: Path, capsys):
        old = tmp_path / "old.json"
        new = tmp_path / "new.json"
        _write_json(old, {"a": 1})
        _write_json(new, {"a": 1})
        rc = main([str(old), str(new), "-q"])
        assert rc == 0
        assert capsys.readouterr().out == ""

    def test_quiet_mode_different(self, tmp_path: Path, capsys):
        old = tmp_path / "old.json"
        new = tmp_path / "new.json"
        _write_json(old, {"a": 1})
        _write_json(new, {"a": 2})
        rc = main([str(old), str(new), "-q"])
        assert rc == 1
        assert capsys.readouterr().out == ""

    def test_missing_file(self, tmp_path: Path):
        old = tmp_path / "nonexistent.json"
        new = tmp_path / "new.json"
        _write_json(new, {"a": 1})
        rc = main([str(old), str(new)])
        assert rc == 2

    def test_yaml_files(self, tmp_path: Path, capsys):
        old = tmp_path / "old.yaml"
        new = tmp_path / "new.yaml"
        old.write_text("host: localhost\nport: 8080\n")
        new.write_text("host: 0.0.0.0\nport: 9090\n")
        rc = main([str(old), str(new)])
        assert rc == 1

    def test_mixed_formats(self, tmp_path: Path, capsys):
        """Can diff a JSON file against a YAML file."""
        old = tmp_path / "old.json"
        new = tmp_path / "new.yaml"
        _write_json(old, {"key": "old_value"})
        new.write_text("key: new_value\n")
        rc = main([str(old), str(new)])
        assert rc == 1
