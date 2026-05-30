"""Tests for the ignore pattern module."""

import pytest
from dictdiff.ignore import IgnoreMatcher, IgnoreRule, filter_dict


class TestIgnoreRule:
    """Tests for IgnoreRule dataclass."""

    def test_exact_key(self):
        rule = IgnoreRule(pattern="password", rule_type="exact")
        assert rule.matches("password", dot_path="parent.password")
        assert not rule.matches("user", dot_path="parent.user")

    def test_glob_pattern(self):
        rule = IgnoreRule(pattern="secret_*", rule_type="glob")
        # Glob matches against the dot_path (full path) when available
        assert rule.matches("secret_key", dot_path="secret_key")
        assert rule.matches("secret_key", dot_path="parent.secret_key") is False
        # This glob matches "secret_*" at the top level
        assert rule.matches("secret_key", dot_path="")

    def test_regex_pattern(self):
        rule = IgnoreRule(pattern=r"^_.*", rule_type="regex")
        # Regex matches against dot_path when provided
        assert rule.matches("_private", dot_path="_private")
        # "obj._private" doesn't start with _, so doesn't match ^_
        assert not rule.matches("_private", dot_path="obj._private")

    def test_dotpath_pattern(self):
        rule = IgnoreRule(pattern="config.db.password", rule_type="dotpath")
        assert rule.matches("password", dot_path="config.db.password")
        assert not rule.matches("password", dot_path="config.api.password")

    def test_prefix_pattern(self):
        rule = IgnoreRule(pattern="metadata.", rule_type="prefix")
        assert rule.matches("key", dot_path="metadata.key")
        assert not rule.matches("key", dot_path="data.key")


class TestIgnoreMatcher:
    """Tests for IgnoreMatcher."""

    def test_empty_matcher(self):
        matcher = IgnoreMatcher()
        assert not matcher.should_ignore("any_key", dot_path="any.path")

    def test_add_exact_rule(self):
        matcher = IgnoreMatcher()
        matcher.add_exact("password")
        assert matcher.should_ignore("password", dot_path="config.password")
        assert not matcher.should_ignore("user", dot_path="config.user")

    def test_add_glob_rule(self):
        matcher = IgnoreMatcher()
        matcher.add_glob("created_at")
        assert matcher.should_ignore("created_at", dot_path="created_at")
        assert matcher.should_ignore("created_at", dot_path="obj.created_at") is False
        # Glob with wildcard matches the full path
        matcher2 = IgnoreMatcher()
        matcher2.add_glob("*_at")
        assert matcher2.should_ignore("created_at", dot_path="created_at")
        assert matcher2.should_ignore("name", dot_path="name") is False

    def test_add_regex_rule(self):
        matcher = IgnoreMatcher()
        matcher.add_regex(r"^_.+")
        # Regex matches against dot_path (full path)
        assert matcher.should_ignore("_internal", dot_path="_internal")
        assert matcher.should_ignore("public", dot_path="public") is False

    def test_add_prefix_rule(self):
        matcher = IgnoreMatcher()
        matcher.add_prefix("metadata.")
        assert matcher.should_ignore("key", dot_path="metadata.key")

    def test_add_dotpath_rule(self):
        matcher = IgnoreMatcher()
        matcher.add_dotpath("config.db.host")
        assert matcher.should_ignore("host", dot_path="config.db.host")
        assert not matcher.should_ignore("host", dot_path="config.api.host")

    def test_multiple_rules(self):
        matcher = IgnoreMatcher()
        matcher.add_exact("password")
        matcher.add_glob("*_at")
        assert matcher.should_ignore("password", dot_path="auth.password")
        assert matcher.should_ignore("created_at", dot_path="obj.created_at")
        assert not matcher.should_ignore("name", dot_path="obj.name")

    def test_from_patterns(self):
        """Test IgnoreMatcher.from_patterns() class method."""
        matcher = IgnoreMatcher.from_patterns([
            "password",           # exact
            "re:^_.*",            # regex
            "secret_*",           # glob (matches dot_path)
            "/config.db.host",    # dotpath
        ])
        # exact matches key name regardless of dot_path
        assert matcher.should_ignore("password", dot_path="auth.password")
        # regex matches the dot_path starting with _
        assert matcher.should_ignore("_private", dot_path="_private")
        # glob matches the dot_path
        assert matcher.should_ignore("key", dot_path="secret_key")
        # dotpath matches exact dot-path
        assert matcher.should_ignore("host", dot_path="config.db.host")
        assert not matcher.should_ignore("name", dot_path="name")


class TestFilterDict:
    """Tests for filter_dict function."""

    def test_filter_no_match(self):
        matcher = IgnoreMatcher()
        data = {"a": 1, "b": 2, "c": 3}
        result = filter_dict(data, matcher)
        assert result == {"a": 1, "b": 2, "c": 3}

    def test_filter_exact_key(self):
        matcher = IgnoreMatcher()
        matcher.add_exact("password")
        data = {"user": "alice", "password": "secret123"}
        result = filter_dict(data, matcher)
        assert "user" in result
        assert "password" not in result

    def test_filter_glob(self):
        matcher = IgnoreMatcher()
        matcher.add_glob("*_at")
        data = {"name": "Alice", "created_at": "2024-01-01", "updated_at": "2024-06-01"}
        result = filter_dict(data, matcher)
        assert "name" in result
        assert "created_at" not in result
        assert "updated_at" not in result

    def test_filter_nested(self):
        matcher = IgnoreMatcher()
        matcher.add_exact("password")
        data = {
            "db": {"host": "localhost", "password": "secret"},
            "api": {"key": "abc", "password": "api_secret"},
        }
        result = filter_dict(data, matcher)
        assert "password" not in result.get("db", {})
        assert "password" not in result.get("api", {})

    def test_filter_deeply_nested(self):
        matcher = IgnoreMatcher()
        matcher.add_exact("token")
        data = {"level1": {"level2": {"level3": {"token": "abc", "value": 42}}}}
        result = filter_dict(data, matcher)
        inner = result.get("level1", {}).get("level2", {}).get("level3", {})
        assert "token" not in inner
        assert "value" in inner

    def test_filter_preserves_non_dict_values(self):
        matcher = IgnoreMatcher()
        data = {"name": "Alice", "scores": [1, 2, 3]}
        result = filter_dict(data, matcher)
        assert result["scores"] == [1, 2, 3]

    def test_filter_empty_dict(self):
        matcher = IgnoreMatcher()
        result = filter_dict({}, matcher)
        assert result == {}

    def test_filter_regex(self):
        matcher = IgnoreMatcher()
        matcher.add_regex(r"^_")
        data = {"public": 1, "_private": 2, "__dunder__": 3}
        result = filter_dict(data, matcher)
        assert "public" in result
        assert "_private" not in result
