"""Ignore patterns — glob and regex patterns for excluding keys/paths
from diff comparison, plus key-prefix and dot-path filtering.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from fnmatch import fnmatch
from typing import Any


@dataclass
class IgnoreRule:
    """A single ignore rule that can match against key names or dot-paths."""

    pattern: str
    rule_type: str = "glob"  # "glob", "regex", "prefix", "exact", "dotpath"
    case_sensitive: bool = True

    _compiled_regex: re.Pattern | None = field(default=None, init=False, repr=False)

    def __post_init__(self) -> None:
        if self.rule_type == "regex":
            flags = 0 if self.case_sensitive else re.IGNORECASE
            self._compiled_regex = re.compile(self.pattern, flags)

    def matches(self, key: str, *, dot_path: str = "") -> bool:
        """Check if this rule matches the given key or dot-path.

        Args:
            key: The key name to check.
            dot_path: The full dot-separated path (e.g. "config.db.host").

        Returns:
            True if the rule matches.
        """
        if self.rule_type == "glob":
            target = dot_path if dot_path else key
            return fnmatch(target, self.pattern)

        if self.rule_type == "regex":
            target = dot_path if dot_path else key
            if self._compiled_regex is None:
                return False
            return bool(self._compiled_regex.search(target))

        if self.rule_type == "prefix":
            target = dot_path if dot_path else key
            return target.startswith(self.pattern)

        if self.rule_type == "exact":
            return key == self.pattern

        if self.rule_type == "dotpath":
            return dot_path == self.pattern if dot_path else key == self.pattern

        return False


@dataclass
class IgnoreMatcher:
    """Collection of ignore rules that can be applied during diff traversal."""

    rules: list[IgnoreRule] = field(default_factory=list)

    def add_glob(self, pattern: str, *, case_sensitive: bool = True) -> None:
        """Add a glob-pattern rule (e.g. 'metadata.*', 'timestamp')."""
        self.rules.append(IgnoreRule(pattern=pattern, rule_type="glob", case_sensitive=case_sensitive))

    def add_regex(self, pattern: str, *, case_sensitive: bool = True) -> None:
        """Add a regex-pattern rule."""
        self.rules.append(IgnoreRule(pattern=pattern, rule_type="regex", case_sensitive=case_sensitive))

    def add_prefix(self, prefix: str) -> None:
        """Add a prefix rule — matches any path starting with this prefix."""
        self.rules.append(IgnoreRule(pattern=prefix, rule_type="prefix"))

    def add_exact(self, key: str) -> None:
        """Add an exact-key rule."""
        self.rules.append(IgnoreRule(pattern=key, rule_type="exact"))

    def add_dotpath(self, path: str) -> None:
        """Add a dot-path rule — matches only the exact dot-path."""
        self.rules.append(IgnoreRule(pattern=path, rule_type="dotpath"))

    def should_ignore(self, key: str, *, dot_path: str = "") -> bool:
        """Check if a key/path should be ignored based on all rules.

        Args:
            key: The key name.
            dot_path: The full dot-path (e.g. "config.db.host").

        Returns:
            True if any rule matches.
        """
        return any(rule.matches(key, dot_path=dot_path) for rule in self.rules)

    @classmethod
    def from_patterns(cls, patterns: list[str]) -> IgnoreMatcher:
        """Create an IgnoreMatcher from a list of pattern strings.

        Auto-detects pattern type:
        - Patterns starting with '/' are treated as dot-path (without the /)
        - Patterns containing *, ?, [ are treated as globs
        - Patterns starting with 're:' are treated as regex
        - Everything else is treated as exact key match

        Args:
            patterns: List of pattern strings.

        Returns:
            Configured IgnoreMatcher.
        """
        matcher = cls()
        for pattern in patterns:
            if pattern.startswith("re:"):
                matcher.add_regex(pattern[3:])
            elif pattern.startswith("/"):
                matcher.add_dotpath(pattern[1:])
            elif any(c in pattern for c in "*?["):
                matcher.add_glob(pattern)
            else:
                matcher.add_exact(pattern)
        return matcher


def filter_dict(
    data: dict[str, Any],
    matcher: IgnoreMatcher,
    *,
    dot_path: str = "",
) -> dict[str, Any]:
    """Filter a dict by removing keys that match ignore rules.

    Recursively walks the dict, applying ignore rules at each level.

    Args:
        data: The dict to filter.
        matcher: The ignore rules to apply.
        dot_path: Current dot-path prefix for rule matching.

    Returns:
        New dict with ignored keys removed.
    """
    result: dict[str, Any] = {}
    for key, value in data.items():
        current_path = f"{dot_path}.{key}" if dot_path else key
        if matcher.should_ignore(key, dot_path=current_path):
            continue
        if isinstance(value, dict):
            filtered = filter_dict(value, matcher, dot_path=current_path)
            result[key] = filtered
        elif isinstance(value, list):
            result[key] = _filter_list(value, matcher, dot_path=current_path)
        else:
            result[key] = value
    return result


def _filter_list(
    data: list[Any],
    matcher: IgnoreMatcher,
    *,
    dot_path: str = "",
) -> list[Any]:
    """Filter a list by applying ignore rules to dict elements."""
    result: list[Any] = []
    for i, item in enumerate(data):
        current_path = f"{dot_path}[{i}]"
        if isinstance(item, dict):
            filtered = filter_dict(item, matcher, dot_path=current_path)
            result.append(filtered)
        elif isinstance(item, list):
            result.append(_filter_list(item, matcher, dot_path=current_path))
        else:
            result.append(item)
    return result
