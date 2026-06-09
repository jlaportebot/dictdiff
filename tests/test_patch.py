"""Tests for dictdiff patch generation and application."""

import pytest
from dictdiff.core import diff
from dictdiff.patch import apply_patch, generate_patch


class TestPatchGeneration:
    """Tests for RFC 6902 JSON Patch generation."""

    def test_added_key(self):
        result = diff({"a": 1}, {"a": 1, "b": 2})
        ops = generate_patch(result)
        assert len(ops) == 1
        assert ops[0] == {"op": "add", "path": "/b", "value": 2}

    def test_removed_key(self):
        result = diff({"a": 1, "b": 2}, {"a": 1})
        ops = generate_patch(result)
        assert len(ops) == 1
        assert ops[0] == {"op": "remove", "path": "/b"}

    def test_changed_value(self):
        result = diff({"a": 1}, {"a": 2})
        ops = generate_patch(result)
        assert len(ops) == 1
        assert ops[0] == {"op": "replace", "path": "/a", "value": 2}

    def test_type_change(self):
        result = diff({"a": "42"}, {"a": 42})
        ops = generate_patch(result)
        assert len(ops) == 1
        assert ops[0] == {"op": "replace", "path": "/a", "value": 42}

    def test_nested_change(self):
        result = diff({"a": {"b": 1}}, {"a": {"b": 2}})
        ops = generate_patch(result)
        assert len(ops) == 1
        assert ops[0] == {"op": "replace", "path": "/a/b", "value": 2}

    def test_empty_diff_no_ops(self):
        result = diff({"a": 1}, {"a": 1})
        ops = generate_patch(result)
        assert ops == []

    def test_multiple_ops(self):
        result = diff({"a": 1, "b": 2, "c": 3}, {"a": 99, "d": 4})
        ops = generate_patch(result)
        ops_set = {(o["op"], o["path"]) for o in ops}
        assert ("replace", "/a") in ops_set
        assert ("remove", "/b") in ops_set
        assert ("remove", "/c") in ops_set
        assert ("add", "/d") in ops_set

    def test_escape_slash_in_key(self):
        result = diff({"a/b": 1}, {"a/b": 2})
        ops = generate_patch(result)
        assert ops[0]["path"] == "/a~1b"

    def test_escape_tilde_in_key(self):
        result = diff({"a~b": 1}, {"a~b": 2})
        ops = generate_patch(result)
        assert ops[0]["path"] == "/a~0b"


class TestPatchApplication:
    """Tests for RFC 6902 JSON Patch application."""

    def test_add_key(self):
        doc = {"a": 1}
        ops = [{"op": "add", "path": "/b", "value": 2}]
        result = apply_patch(doc, ops)
        assert result == {"a": 1, "b": 2}

    def test_remove_key(self):
        doc = {"a": 1, "b": 2}
        ops = [{"op": "remove", "path": "/b"}]
        result = apply_patch(doc, ops)
        assert result == {"a": 1}

    def test_replace_key(self):
        doc = {"a": 1}
        ops = [{"op": "replace", "path": "/a", "value": 99}]
        result = apply_patch(doc, ops)
        assert result == {"a": 99}

    def test_nested_add(self):
        doc = {"a": {"b": 1}}
        ops = [{"op": "add", "path": "/a/c", "value": 2}]
        result = apply_patch(doc, ops)
        assert result == {"a": {"b": 1, "c": 2}}

    def test_nested_replace(self):
        doc = {"a": {"b": 1}}
        ops = [{"op": "replace", "path": "/a/b", "value": 99}]
        result = apply_patch(doc, ops)
        assert result == {"a": {"b": 99}}

    def test_does_not_mutate_original(self):
        doc = {"a": 1}
        ops = [{"op": "add", "path": "/b", "value": 2}]
        result = apply_patch(doc, ops)
        assert doc == {"a": 1}
        assert result == {"a": 1, "b": 2}

    def test_add_to_list(self):
        doc = {"items": [1, 2]}
        ops = [{"op": "add", "path": "/items/2", "value": 3}]
        result = apply_patch(doc, ops)
        assert result == {"items": [1, 2, 3]}

    def test_remove_from_list(self):
        doc = {"items": [1, 2, 3]}
        ops = [{"op": "remove", "path": "/items/1"}]
        result = apply_patch(doc, ops)
        assert result == {"items": [1, 3]}

    def test_roundtrip(self):
        """Generate patch, apply it, and verify the result matches."""
        old = {"a": 1, "b": {"c": 2, "d": [1, 2, 3]}, "e": "hello"}
        new = {"a": 99, "b": {"c": 2, "d": [1, 99, 3], "f": 4}, "g": True}
        result = diff(old, new)
        ops = generate_patch(result)
        patched = apply_patch(old, ops)
        assert patched == new

    def test_roundtrip_complex(self):
        """More complex roundtrip test."""
        old = {
            "config": {
                "db": {"host": "localhost", "port": 5432},
                "cache": {"enabled": True},
            },
            "version": 1,
        }
        new = {
            "config": {
                "db": {"host": "prod-server", "port": 5432},
                "cache": {"enabled": False, "ttl": 300},
            },
            "version": 2,
        }
        result = diff(old, new)
        ops = generate_patch(result)
        patched = apply_patch(old, ops)
        assert patched == new

    def test_unsupported_op(self):
        with pytest.raises(ValueError, match="Unsupported operation"):
            apply_patch({"a": 1}, [{"op": "copy", "from": "/a", "path": "/b"}])
