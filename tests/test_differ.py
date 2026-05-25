"""Tests for dictdiff core differ logic."""

from __future__ import annotations

import pytest

from dictdiff.differ import (
    ChangeKind,
    DiffEntry,
    count_changes,
    diff_dicts,
    flatten,
    _type_name,
    _values_equal,
)


class TestTypeName:
    def test_none(self):
        assert _type_name(None) == "null"

    def test_bool(self):
        assert _type_name(True) == "bool"
        assert _type_name(False) == "bool"

    def test_int(self):
        assert _type_name(42) == "int"

    def test_float(self):
        assert _type_name(3.14) == "float"

    def test_str(self):
        assert _type_name("hello") == "str"

    def test_list(self):
        assert _type_name([1, 2]) == "list"

    def test_dict(self):
        assert _type_name({"a": 1}) == "dict"

    def test_custom(self):
        assert _type_name(set()) == "set"


class TestValuesEqual:
    def test_same_primitives(self):
        assert _values_equal(1, 1) is True
        assert _values_equal("a", "a") is True

    def test_different_primitives(self):
        assert _values_equal(1, 2) is False
        assert _values_equal("a", "b") is False

    def test_different_types(self):
        assert _values_equal(1, "1") is False

    def test_same_dicts(self):
        assert _values_equal({"a": 1}, {"a": 1}) is True

    def test_different_dicts(self):
        assert _values_equal({"a": 1}, {"a": 2}) is False
        assert _values_equal({"a": 1}, {"b": 1}) is False

    def test_same_lists(self):
        assert _values_equal([1, 2, 3], [1, 2, 3]) is True

    def test_different_lists(self):
        assert _values_equal([1, 2], [1, 3]) is False
        assert _values_equal([1, 2], [1, 2, 3]) is False

    def test_nested(self):
        a = {"x": [1, {"y": 2}]}
        b = {"x": [1, {"y": 2}]}
        c = {"x": [1, {"y": 3}]}
        assert _values_equal(a, b) is True
        assert _values_equal(a, c) is False


class TestDiffDicts:
    def test_identical(self):
        result = diff_dicts({"a": 1}, {"a": 1})
        assert result == []

    def test_added(self):
        result = diff_dicts({"a": 1}, {"a": 1, "b": 2})
        assert len(result) == 1
        assert result[0].kind == ChangeKind.ADDED
        assert result[0].path == "b"
        assert result[0].new_value == 2

    def test_removed(self):
        result = diff_dicts({"a": 1, "b": 2}, {"a": 1})
        assert len(result) == 1
        assert result[0].kind == ChangeKind.REMOVED
        assert result[0].path == "b"
        assert result[0].old_value == 2

    def test_value_changed(self):
        result = diff_dicts({"a": 1}, {"a": 2})
        assert len(result) == 1
        assert result[0].kind == ChangeKind.VALUE_CHANGED
        assert result[0].old_value == 1
        assert result[0].new_value == 2

    def test_type_changed(self):
        result = diff_dicts({"a": 1}, {"a": "1"})
        assert len(result) == 1
        assert result[0].kind == ChangeKind.TYPE_CHANGED
        assert result[0].old_type == "int"
        assert result[0].new_type == "str"

    def test_nested_changes(self):
        old = {"config": {"host": "localhost", "port": 8080}}
        new = {"config": {"host": "0.0.0.0", "port": 8080}}
        result = diff_dicts(old, new)
        assert len(result) == 1
        assert result[0].kind == ChangeKind.UNCHANGED
        assert len(result[0].children) == 1
        assert result[0].children[0].kind == ChangeKind.VALUE_CHANGED
        assert result[0].children[0].path == "config.host"

    def test_nested_added(self):
        old = {"config": {"host": "localhost"}}
        new = {"config": {"host": "localhost", "port": 8080}}
        result = diff_dicts(old, new)
        assert len(result) == 1
        child = result[0].children[0]
        assert child.kind == ChangeKind.ADDED
        assert child.path == "config.port"

    def test_nested_removed(self):
        old = {"config": {"host": "localhost", "port": 8080}}
        new = {"config": {"host": "localhost"}}
        result = diff_dicts(old, new)
        assert len(result) == 1
        child = result[0].children[0]
        assert child.kind == ChangeKind.REMOVED
        assert child.path == "config.port"

    def test_list_changed(self):
        result = diff_dicts({"items": [1, 2, 3]}, {"items": [1, 2, 4]})
        assert len(result) == 1
        assert result[0].kind == ChangeKind.VALUE_CHANGED

    def test_list_unchanged(self):
        result = diff_dicts({"items": [1, 2, 3]}, {"items": [1, 2, 3]})
        assert result == []

    def test_multiple_changes(self):
        old = {"a": 1, "b": "hello", "c": [1, 2]}
        new = {"a": 2, "b": "hello", "d": True}
        result = diff_dicts(old, new)
        kinds = {e.kind for e in result}
        assert ChangeKind.VALUE_CHANGED in kinds  # a: 1 -> 2
        assert ChangeKind.REMOVED in kinds  # c removed
        assert ChangeKind.ADDED in kinds  # d added

    def test_deeply_nested(self):
        old = {"a": {"b": {"c": {"d": 1}}}}
        new = {"a": {"b": {"c": {"d": 2}}}}
        result = diff_dicts(old, new)
        flat = flatten(result)
        assert len(flat) == 1
        assert flat[0].path == "a.b.c.d"
        assert flat[0].kind == ChangeKind.VALUE_CHANGED

    def test_bool_vs_int_type_change(self):
        """bool is a subclass of int in Python — we handle it explicitly."""
        result = diff_dicts({"flag": 1}, {"flag": True})
        assert len(result) == 1
        assert result[0].kind == ChangeKind.TYPE_CHANGED

    def test_empty_dicts(self):
        result = diff_dicts({}, {})
        assert result == []

    def test_none_vs_missing(self):
        result = diff_dicts({"a": None}, {"a": 1})
        assert len(result) == 1
        assert result[0].kind == ChangeKind.TYPE_CHANGED
        assert result[0].old_type == "null"


class TestCountChanges:
    def test_no_changes(self):
        assert count_changes([]) == {"added": 0, "removed": 0, "type_changed": 0, "value_changed": 0}

    def test_counts_flat(self):
        entries = [
            DiffEntry(path="a", kind=ChangeKind.ADDED, new_value=1),
            DiffEntry(path="b", kind=ChangeKind.REMOVED, old_value=2),
            DiffEntry(path="c", kind=ChangeKind.VALUE_CHANGED, old_value=3, new_value=4),
        ]
        counts = count_changes(entries)
        assert counts["added"] == 1
        assert counts["removed"] == 1
        assert counts["value_changed"] == 1

    def test_counts_nested(self):
        entries = [
            DiffEntry(
                path="config",
                kind=ChangeKind.UNCHANGED,
                children=[
                    DiffEntry(path="config.host", kind=ChangeKind.VALUE_CHANGED, old_value="a", new_value="b"),
                    DiffEntry(path="config.port", kind=ChangeKind.ADDED, new_value=8080),
                ],
            )
        ]
        counts = count_changes(entries)
        assert counts["value_changed"] == 1
        assert counts["added"] == 1


class TestFlatten:
    def test_empty(self):
        assert flatten([]) == []

    def test_flat_entries(self):
        entries = [
            DiffEntry(path="a", kind=ChangeKind.ADDED, new_value=1),
            DiffEntry(path="b", kind=ChangeKind.REMOVED, old_value=2),
        ]
        flat = flatten(entries)
        assert len(flat) == 2
        assert flat[0].path == "a"
        assert flat[1].path == "b"

    def test_nested_entries(self):
        entries = [
            DiffEntry(
                path="config",
                kind=ChangeKind.UNCHANGED,
                children=[
                    DiffEntry(path="config.host", kind=ChangeKind.VALUE_CHANGED, old_value="a", new_value="b"),
                    DiffEntry(path="config.port", kind=ChangeKind.ADDED, new_value=8080),
                ],
            )
        ]
        flat = flatten(entries)
        assert len(flat) == 2
        assert flat[0].path == "config.host"
        assert flat[1].path == "config.port"
