"""Tests for the three-way merge module."""

from dictdiff.merge3 import merge3, MergeResult


class TestMerge3Simple:
    """Basic three-way merge tests."""

    def test_no_changes(self):
        """Both sides unchanged from base."""
        base = {"a": 1, "b": 2}
        ours = {"a": 1, "b": 2}
        theirs = {"a": 1, "b": 2}
        result = merge3(base, ours, theirs)
        assert result.merged == {"a": 1, "b": 2}
        assert not result.has_conflicts

    def test_ours_only_changed(self):
        """Only ours changed a key."""
        base = {"a": 1, "b": 2}
        ours = {"a": 10, "b": 2}
        theirs = {"a": 1, "b": 2}
        result = merge3(base, ours, theirs)
        assert result.merged["a"] == 10
        assert not result.has_conflicts

    def test_theirs_only_changed(self):
        """Only theirs changed a key."""
        base = {"a": 1, "b": 2}
        ours = {"a": 1, "b": 2}
        theirs = {"a": 1, "b": 20}
        result = merge3(base, ours, theirs)
        assert result.merged["b"] == 20
        assert not result.has_conflicts

    def test_both_changed_same_key_differently(self):
        """Both changed same key to different values → conflict."""
        base = {"a": 1}
        ours = {"a": 10}
        theirs = {"a": 20}
        result = merge3(base, ours, theirs)
        assert result.has_conflicts
        assert result.conflict_count >= 1

    def test_both_changed_same_key_identically(self):
        """Both changed same key to the same value → no conflict."""
        base = {"a": 1}
        ours = {"a": 10}
        theirs = {"a": 10}
        result = merge3(base, ours, theirs)
        assert not result.has_conflicts
        assert result.merged["a"] == 10

    def test_ours_adds_key(self):
        """Ours adds a new key."""
        base = {"a": 1}
        ours = {"a": 1, "b": 2}
        theirs = {"a": 1}
        result = merge3(base, ours, theirs)
        assert result.merged.get("b") == 2
        assert not result.has_conflicts

    def test_theirs_adds_key(self):
        """Theirs adds a new key."""
        base = {"a": 1}
        ours = {"a": 1}
        theirs = {"a": 1, "c": 3}
        result = merge3(base, ours, theirs)
        assert result.merged.get("c") == 3
        assert not result.has_conflicts

    def test_both_add_same_key(self):
        """Both add the same key with the same value."""
        base = {"a": 1}
        ours = {"a": 1, "b": 2}
        theirs = {"a": 1, "b": 2}
        result = merge3(base, ours, theirs)
        assert result.merged["b"] == 2
        assert not result.has_conflicts

    def test_both_add_same_key_different_value(self):
        """Both add the same key with different values → conflict."""
        base = {"a": 1}
        ours = {"a": 1, "b": 10}
        theirs = {"a": 1, "b": 20}
        result = merge3(base, ours, theirs)
        assert result.has_conflicts

    def test_ours_deletes_key(self):
        """Ours deletes a key."""
        base = {"a": 1, "b": 2}
        ours = {"a": 1}
        theirs = {"a": 1, "b": 2}
        result = merge3(base, ours, theirs)
        assert "b" not in result.merged
        assert not result.has_conflicts

    def test_theirs_deletes_key(self):
        """Theirs deletes a key."""
        base = {"a": 1, "b": 2}
        ours = {"a": 1, "b": 2}
        theirs = {"a": 1}
        result = merge3(base, ours, theirs)
        assert "b" not in result.merged
        assert not result.has_conflicts

    def test_one_deletes_other_modifies(self):
        """One side deletes a key, other modifies it → conflict."""
        base = {"a": 1, "b": 2}
        ours = {"a": 1}  # deleted b
        theirs = {"a": 1, "b": 20}  # modified b
        result = merge3(base, ours, theirs)
        assert result.has_conflicts


class TestMerge3Nested:
    """Three-way merge with nested dicts."""

    def test_nested_ours_changed(self):
        base = {"db": {"host": "localhost", "port": 5432}}
        ours = {"db": {"host": "remote", "port": 5432}}
        theirs = {"db": {"host": "localhost", "port": 5432}}
        result = merge3(base, ours, theirs)
        assert result.merged["db"]["host"] == "remote"
        assert not result.has_conflicts

    def test_nested_both_changed_different_keys(self):
        base = {"db": {"host": "localhost", "port": 5432}}
        ours = {"db": {"host": "remote", "port": 5432}}
        theirs = {"db": {"host": "localhost", "port": 3306}}
        result = merge3(base, ours, theirs)
        assert result.merged["db"]["host"] == "remote"
        assert result.merged["db"]["port"] == 3306
        assert not result.has_conflicts

    def test_nested_both_changed_same_key(self):
        base = {"db": {"host": "localhost", "port": 5432}}
        ours = {"db": {"host": "ours-host", "port": 5432}}
        theirs = {"db": {"host": "theirs-host", "port": 5432}}
        result = merge3(base, ours, theirs)
        assert result.has_conflicts


class TestMerge3Lists:
    """Three-way merge with lists."""

    def test_ours_changed_list(self):
        base = {"items": [1, 2, 3]}
        ours = {"items": [1, 2, 3, 4]}
        theirs = {"items": [1, 2, 3]}
        result = merge3(base, ours, theirs)
        assert not result.has_conflicts

    def test_both_changed_list(self):
        base = {"items": [1, 2, 3]}
        ours = {"items": [1, 2, 3, 4]}
        theirs = {"items": [1, 2, 3, 5]}
        result = merge3(base, ours, theirs)
        # List changes from both sides may conflict
        assert isinstance(result, MergeResult)


class TestMerge3ConflictResolution:
    """Tests for conflict resolution preferences."""

    def test_ours_wins(self):
        base = {"a": 1}
        ours = {"a": 10}
        theirs = {"a": 20}
        result = merge3(base, ours, theirs, ours_wins=True)
        assert result.has_conflicts
        # With ours_wins, the merged value should prefer ours
        assert result.merged.get("a") == 10

    def test_theirs_wins(self):
        base = {"a": 1}
        ours = {"a": 10}
        theirs = {"a": 20}
        result = merge3(base, ours, theirs, ours_wins=False)
        assert result.has_conflicts
        # With theirs_wins, the merged value should prefer theirs
        assert result.merged.get("a") == 20


class TestMerge3Summary:
    """Tests for MergeResult.summary()."""

    def test_summary_no_conflicts(self):
        base = {"a": 1}
        ours = {"a": 10}
        theirs = {"a": 1}
        result = merge3(base, ours, theirs)
        s = result.summary()
        assert s["conflict_count"] == 0
        assert s["has_conflicts"] is False

    def test_summary_with_conflicts(self):
        base = {"a": 1}
        ours = {"a": 10}
        theirs = {"a": 20}
        result = merge3(base, ours, theirs)
        s = result.summary()
        assert s["has_conflicts"] is True
        assert s["conflict_count"] >= 1


class TestMerge3Empty:
    """Edge cases with empty dicts."""

    def test_all_empty(self):
        result = merge3({}, {}, {})
        assert result.merged == {}
        assert not result.has_conflicts

    def test_base_empty_both_add(self):
        result = merge3({}, {"a": 1}, {"b": 2})
        assert result.merged.get("a") == 1
        assert result.merged.get("b") == 2
        assert not result.has_conflicts

    def test_base_empty_conflict(self):
        result = merge3({}, {"a": 1}, {"a": 2})
        assert result.has_conflicts
