"""Tests for dictdiff convenience functions."""

import json

from dictdiff.convenience import diff_files, diff_strings, diff_to_patch
from dictdiff.core import Change


class TestDiffStrings:
    """Tests for diff_strings convenience function."""

    def test_identical(self):
        result = diff_strings('{"a": 1}', '{"a": 1}')
        assert result.is_empty

    def test_different(self):
        result = diff_strings('{"a": 1}', '{"a": 2}')
        assert result.changed == {"a": Change(old=1, new=2)}

    def test_nested(self):
        old = json.dumps({"a": {"b": 1}})
        new = json.dumps({"a": {"b": 2}})
        result = diff_strings(old, new)
        assert "a" in result.children

    def test_set_mode(self):
        old = json.dumps([1, 2, 3])
        new = json.dumps([3, 2, 1])
        result = diff_strings(old, new, set_mode=True)
        assert result.is_empty

    def test_ignore_keys(self):
        old = json.dumps({"a": 1, "b": 2})
        new = json.dumps({"a": 1, "b": 99})
        result = diff_strings(old, new, ignore_keys={"b"})
        assert result.is_empty

    def test_float_tolerance(self):
        old = json.dumps({"x": 1.0})
        new = json.dumps({"x": 1.0001})
        result = diff_strings(old, new, float_tolerance=0.001)
        assert result.is_empty


class TestDiffFiles:
    """Tests for diff_files convenience function."""

    def test_file_diff(self, tmp_path):
        old_path = tmp_path / "old.json"
        new_path = tmp_path / "new.json"
        old_path.write_text(json.dumps({"a": 1, "b": 2}))
        new_path.write_text(json.dumps({"a": 1, "b": 99, "c": 3}))

        result = diff_files(str(old_path), str(new_path))
        assert not result.is_empty
        assert result.changed == {"b": Change(old=2, new=99)}
        assert result.added == {"c": 3}

    def test_identical_files(self, tmp_path):
        p1 = tmp_path / "a.json"
        p2 = tmp_path / "b.json"
        p1.write_text(json.dumps({"x": 1}))
        p2.write_text(json.dumps({"x": 1}))

        result = diff_files(str(p1), str(p2))
        assert result.is_empty

    def test_path_objects(self, tmp_path):
        old_path = tmp_path / "old.json"
        new_path = tmp_path / "new.json"
        old_path.write_text(json.dumps({"a": 1}))
        new_path.write_text(json.dumps({"a": 2}))

        result = diff_files(old_path, new_path)
        assert result.changed == {"a": Change(old=1, new=2)}


class TestDiffToPatch:
    """Tests for diff_to_patch convenience function."""

    def test_generates_patch(self):
        ops = diff_to_patch({"a": 1}, {"a": 2})
        assert len(ops) == 1
        assert ops[0]["op"] == "replace"
        assert ops[0]["path"] == "/a"
        assert ops[0]["value"] == 2

    def test_no_changes(self):
        ops = diff_to_patch({"a": 1}, {"a": 1})
        assert ops == []

    def test_complex_patch(self):
        old = {"a": 1, "b": [1, 2], "c": "old"}
        new = {"a": 99, "b": [1, 3], "d": "new"}
        ops = diff_to_patch(old, new)
        ops_set = {o["op"] for o in ops}
        assert "replace" in ops_set
        assert "add" in ops_set or "remove" in ops_set
