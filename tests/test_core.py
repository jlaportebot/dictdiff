"""Tests for dictdiff core diff logic."""

import pytest
from dictdiff.core import Change, DiffResult, diff


class TestScalarDiff:
    """Tests for scalar value comparison."""

    def test_identical_scalars(self):
        result = diff(1, 1)
        assert result.is_empty

    def test_different_scalars(self):
        result = diff(1, 2)
        assert not result.is_empty
        assert result.changed == {"": Change(old=1, new=2)}

    def test_identical_strings(self):
        result = diff("hello", "hello")
        assert result.is_empty

    def test_different_strings(self):
        result = diff("hello", "world")
        assert result.changed == {"": Change(old="hello", new="world")}

    def test_none_values(self):
        result = diff(None, None)
        assert result.is_empty

    def test_none_vs_value(self):
        result = diff(None, 0)
        assert result.type_changed == {"": Change(old=None, new=0)}

    def test_bool_values(self):
        result = diff(True, False)
        assert result.changed == {"": Change(old=True, new=False)}


class TestTypeChanges:
    """Tests for type change detection."""

    def test_string_to_int(self):
        result = diff("42", 42)
        assert result.type_changed == {"": Change(old="42", new=42)}

    def test_int_to_string(self):
        result = diff(42, "42")
        assert result.type_changed == {"": Change(old=42, new="42")}

    def test_int_to_float_compatible(self):
        """int and float are compatible numeric types — type change NOT flagged."""
        result = diff(42, 42.0)
        assert result.is_empty

    def test_int_to_float_different(self):
        """int and float with different values — value change, not type change."""
        result = diff(42, 42.5)
        assert result.changed == {"": Change(old=42, new=42.5)}

    def test_list_to_dict(self):
        result = diff([1, 2], {"a": 1})
        assert result.type_changed == {"": Change(old=[1, 2], new={"a": 1})}

    def test_none_to_list(self):
        result = diff(None, [1])
        assert result.type_changed == {"": Change(old=None, new=[1])}


class TestFloatTolerance:
    """Tests for float tolerance comparison."""

    def test_within_tolerance(self):
        result = diff(1.0, 1.0001, float_tolerance=0.001)
        assert result.is_empty

    def test_outside_tolerance(self):
        result = diff(1.0, 1.01, float_tolerance=0.001)
        assert not result.is_empty
        assert result.changed == {"": Change(old=1.0, new=1.01)}

    def test_exact_tolerance(self):
        result = diff(1.0, 1.001, float_tolerance=0.001)
        assert result.is_empty

    def test_int_float_tolerance(self):
        result = diff(1, 1.0001, float_tolerance=0.001)
        assert result.is_empty


class TestDictDiff:
    """Tests for dict comparison."""

    def test_identical_dicts(self):
        result = diff({"a": 1, "b": 2}, {"a": 1, "b": 2})
        assert result.is_empty

    def test_added_key(self):
        result = diff({"a": 1}, {"a": 1, "b": 2})
        assert result.added == {"b": 2}
        assert result.removed == {}

    def test_removed_key(self):
        result = diff({"a": 1, "b": 2}, {"a": 1})
        assert result.removed == {"b": 2}
        assert result.added == {}

    def test_changed_value(self):
        result = diff({"a": 1}, {"a": 2})
        assert result.changed == {"a": Change(old=1, new=2)}

    def test_nested_dict_change(self):
        result = diff({"a": {"b": 1}}, {"a": {"b": 2}})
        assert "a" in result.children
        assert result.children["a"].changed == {"b": Change(old=1, new=2)}

    def test_nested_dict_added(self):
        result = diff({"a": {}}, {"a": {"b": 1}})
        assert "a" in result.children
        assert result.children["a"].added == {"b": 1}

    def test_nested_dict_removed(self):
        result = diff({"a": {"b": 1}}, {"a": {}})
        assert "a" in result.children
        assert result.children["a"].removed == {"b": 1}

    def test_deep_nesting(self):
        old = {"a": {"b": {"c": {"d": 1}}}}
        new = {"a": {"b": {"c": {"d": 2}}}}
        result = diff(old, new)
        assert not result.is_empty
        assert "a" in result.children
        assert "b" in result.children["a"].children
        assert "c" in result.children["a"].children["b"].children
        assert result.children["a"].children["b"].children["c"].changed == {"d": Change(old=1, new=2)}

    def test_type_change_in_dict(self):
        result = diff({"a": "42"}, {"a": 42})
        assert result.type_changed == {"a": Change(old="42", new=42)}

    def test_ignore_keys(self):
        result = diff({"a": 1, "b": 2, "c": 3}, {"a": 1, "b": 99, "c": 3}, ignore_keys={"b"})
        assert result.is_empty

    def test_multiple_changes(self):
        old = {"a": 1, "b": 2, "c": 3}
        new = {"a": 1, "b": 99, "d": 4}
        result = diff(old, new)
        assert result.changed == {"b": Change(old=2, new=99)}
        assert result.removed == {"c": 3}
        assert result.added == {"d": 4}

    def test_empty_dicts(self):
        result = diff({}, {})
        assert result.is_empty


class TestListDiff:
    """Tests for list comparison."""

    def test_identical_lists(self):
        result = diff([1, 2, 3], [1, 2, 3])
        assert result.is_empty

    def test_added_elements(self):
        result = diff([1, 2], [1, 2, 3])
        assert result.added == {"2": 3}

    def test_removed_elements(self):
        result = diff([1, 2, 3], [1, 2])
        assert result.removed == {"2": 3}

    def test_changed_element(self):
        result = diff([1, 2, 3], [1, 99, 3])
        assert result.changed == {"1": Change(old=2, new=99)}

    def test_type_change_in_list(self):
        result = diff([1, "2"], [1, 2])
        assert result.type_changed == {"1": Change(old="2", new=2)}

    def test_nested_list(self):
        result = diff([[1, 2]], [[1, 3]])
        assert "0" in result.children
        assert result.children["0"].changed == {"1": Change(old=2, new=3)}

    def test_list_of_dicts(self):
        old = [{"name": "Alice"}, {"name": "Bob"}]
        new = [{"name": "Alice"}, {"name": "Charlie"}]
        result = diff(old, new)
        assert "1" in result.children
        assert result.children["1"].changed == {"name": Change(old="Bob", new="Charlie")}


class TestListSetMode:
    """Tests for set-mode list comparison."""

    def test_identical_sets(self):
        result = diff([1, 2, 3], [3, 2, 1], set_mode=True)
        assert result.is_empty

    def test_added_item(self):
        result = diff([1, 2], [1, 2, 3], set_mode=True)
        assert 3 in result.added.values()

    def test_removed_item(self):
        result = diff([1, 2, 3], [1, 2], set_mode=True)
        assert 3 in result.removed.values()

    def test_order_irrelevant(self):
        result = diff([1, 2, 3], [3, 1, 2], set_mode=True)
        assert result.is_empty

    def test_dict_items_in_set_mode(self):
        old = [{"id": 1}, {"id": 2}]
        new = [{"id": 2}, {"id": 3}]
        result = diff(old, new, set_mode=True)
        assert not result.is_empty


class TestDiffResultSummary:
    """Tests for DiffResult.summary()."""

    def test_empty_summary(self):
        result = diff({"a": 1}, {"a": 1})
        assert result.summary() == {"added": 0, "removed": 0, "changed": 0, "type_changed": 0}

    def test_added_summary(self):
        result = diff({}, {"a": 1, "b": 2})
        s = result.summary()
        assert s["added"] == 2

    def test_mixed_summary(self):
        result = diff({"a": 1, "b": 2}, {"a": 99, "c": 3})
        s = result.summary()
        assert s["added"] == 1
        assert s["removed"] == 1
        assert s["changed"] == 1

    def test_nested_summary(self):
        result = diff({"a": {"b": 1, "c": 2}}, {"a": {"b": 99, "d": 3}})
        s = result.summary()
        assert s["changed"] == 1
        assert s["added"] == 1
        assert s["removed"] == 1


class TestEdgeCases:
    """Tests for edge cases and unusual inputs."""

    def test_empty_input(self):
        result = diff({}, {})
        assert result.is_empty

    def test_empty_vs_nonempty(self):
        result = diff({}, {"a": 1})
        assert result.added == {"a": 1}

    def test_deeply_nested_identical(self):
        data = {"a": {"b": {"c": {"d": {"e": 1}}}}}
        result = diff(data, data)
        assert result.is_empty

    def test_unicode_values(self):
        result = diff("café", "café")
        assert result.is_empty

    def test_bool_vs_int_type(self):
        """bool is a subclass of int, but type(True) != type(1)."""
        result = diff(True, 1)
        assert result.type_changed == {"": Change(old=True, new=1)}

    def test_large_dicts(self):
        old = {str(i): i for i in range(1000)}
        new = {str(i): i for i in range(1000)}
        result = diff(old, new)
        assert result.is_empty

    def test_nested_list_in_dict(self):
        old = {"items": [1, 2, 3]}
        new = {"items": [1, 2, 4]}
        result = diff(old, new)
        assert "items" in result.children
        assert result.children["items"].changed == {"2": Change(old=3, new=4)}
