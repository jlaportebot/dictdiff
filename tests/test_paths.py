"""Tests for the paths module."""

import pytest
from dictdiff.paths import extract_path, list_paths, path_exists, set_path, remove_path


class TestExtractPath:
    """Tests for extract_path function."""

    def test_simple_key(self):
        data = {"name": "Alice"}
        assert extract_path(data, "name") == "Alice"

    def test_nested_key(self):
        data = {"db": {"host": "localhost", "port": 5432}}
        assert extract_path(data, "db.host") == "localhost"
        assert extract_path(data, "db.port") == 5432

    def test_deep_nesting(self):
        data = {"a": {"b": {"c": {"d": 42}}}}
        assert extract_path(data, "a.b.c.d") == 42

    def test_list_index(self):
        data = {"items": [10, 20, 30]}
        assert extract_path(data, "items.1") == 20

    def test_missing_key_raises(self):
        data = {"name": "Alice"}
        with pytest.raises(KeyError):
            extract_path(data, "missing")

    def test_missing_nested_key_raises(self):
        data = {"a": {"b": 1}}
        with pytest.raises(KeyError):
            extract_path(data, "a.c")

    def test_empty_path_returns_data(self):
        data = {"key": "value"}
        assert extract_path(data, "") == data

    def test_dict_at_path(self):
        data = {"db": {"host": "localhost", "port": 5432}}
        result = extract_path(data, "db")
        assert result == {"host": "localhost", "port": 5432}


class TestListPaths:
    """Tests for list_paths function."""

    def test_flat_dict(self):
        data = {"a": 1, "b": 2, "c": 3}
        paths = list_paths(data)
        assert set(paths) == {"a", "b", "c"}

    def test_nested_dict(self):
        data = {"a": {"b": 1, "c": 2}, "d": 3}
        paths = list_paths(data)
        assert "a.b" in paths
        assert "a.c" in paths
        assert "d" in paths

    def test_deeply_nested(self):
        data = {"x": {"y": {"z": 42}}}
        paths = list_paths(data)
        assert "x.y.z" in paths

    def test_list_values(self):
        data = {"items": [1, 2, 3]}
        paths = list_paths(data)
        assert "items" in paths  # Lists are leaf values

    def test_empty_dict(self):
        assert list_paths({}) == []

    def test_none_value(self):
        data = {"key": None}
        paths = list_paths(data)
        assert "key" in paths

    def test_mixed_nesting(self):
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


class TestPathExists:
    """Tests for path_exists function."""

    def test_existing_path(self):
        data = {"a": {"b": 1}}
        assert path_exists(data, "a.b") is True

    def test_missing_path(self):
        data = {"a": {"b": 1}}
        assert path_exists(data, "a.c") is False

    def test_top_level(self):
        data = {"key": "value"}
        assert path_exists(data, "key") is True
        assert path_exists(data, "missing") is False

    def test_empty_data(self):
        assert path_exists({}, "anything") is False


class TestSetPath:
    """Tests for set_path function."""

    def test_set_existing_key(self):
        data = {"a": 1, "b": 2}
        set_path(data, "a", 10)
        assert data["a"] == 10

    def test_set_nested_key(self):
        data = {"a": {"b": 1}}
        set_path(data, "a.b", 10)
        assert data["a"]["b"] == 10

    def test_set_new_key(self):
        data = {"a": 1}
        set_path(data, "b", 2)
        assert data["b"] == 2

    def test_set_deeply_nested_new(self):
        data = {}
        set_path(data, "a.b.c", 42)
        assert data["a"]["b"]["c"] == 42


class TestRemovePath:
    """Tests for remove_path function."""

    def test_remove_existing_key(self):
        data = {"a": 1, "b": 2}
        remove_path(data, "a")
        assert "a" not in data

    def test_remove_nested_key(self):
        data = {"a": {"b": 1, "c": 2}}
        remove_path(data, "a.b")
        assert "b" not in data["a"]
        assert "c" in data["a"]

    def test_remove_missing_key_raises(self):
        data = {"a": 1}
        with pytest.raises(KeyError):
            remove_path(data, "missing")

    def test_remove_nested_missing_raises(self):
        data = {"a": {"b": 1}}
        with pytest.raises(KeyError):
            remove_path(data, "a.c")
        assert data["a"]["b"] == 1
