"""Tests for dictdiff loader."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest
import yaml

from dictdiff.loader import load_file


class TestLoadJson:
    def test_valid_json(self, tmp_path: Path):
        p = tmp_path / "test.json"
        p.write_text('{"a": 1, "b": "hello"}')
        result = load_file(p)
        assert result == {"a": 1, "b": "hello"}

    def test_empty_object(self, tmp_path: Path):
        p = tmp_path / "empty.json"
        p.write_text("{}")
        assert load_file(p) == {}

    def test_nested_json(self, tmp_path: Path):
        p = tmp_path / "nested.json"
        p.write_text('{"a": {"b": {"c": 1}}}')
        assert load_file(p) == {"a": {"b": {"c": 1}}}

    def test_non_dict_json(self, tmp_path: Path):
        p = tmp_path / "array.json"
        p.write_text("[1, 2, 3]")
        with pytest.raises(ValueError, match="Expected a JSON object"):
            load_file(p)


class TestLoadYaml:
    def test_valid_yaml(self, tmp_path: Path):
        p = tmp_path / "test.yaml"
        p.write_text("a: 1\nb: hello\n")
        result = load_file(p)
        assert result == {"a": 1, "b": "hello"}

    def test_yml_extension(self, tmp_path: Path):
        p = tmp_path / "test.yml"
        p.write_text("key: value\n")
        assert load_file(p) == {"key": "value"}

    def test_empty_yaml(self, tmp_path: Path):
        p = tmp_path / "empty.yaml"
        p.write_text("")
        assert load_file(p) == {}

    def test_nested_yaml(self, tmp_path: Path):
        p = tmp_path / "nested.yaml"
        p.write_text("a:\n  b:\n    c: 1\n")
        assert load_file(p) == {"a": {"b": {"c": 1}}}

    def test_non_dict_yaml(self, tmp_path: Path):
        p = tmp_path / "list.yaml"
        p.write_text("- 1\n- 2\n")
        with pytest.raises(ValueError, match="Expected a YAML mapping"):
            load_file(p)


class TestLoadFileErrors:
    def test_file_not_found(self):
        with pytest.raises(FileNotFoundError):
            load_file("/nonexistent/file.json")

    def test_unsupported_format(self, tmp_path: Path):
        p = tmp_path / "data.csv"
        p.write_text("a,b\n1,2")
        with pytest.raises(ValueError, match="Unsupported format"):
            load_file(p)

    def test_directory(self, tmp_path: Path):
        with pytest.raises(ValueError, match="Not a file"):
            load_file(tmp_path)
