"""Core diff logic — recursive dict/list/scalar comparison."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Change:
    """A single value change (old → new)."""

    old: Any
    new: Any

    def __repr__(self) -> str:
        return f"Change(old={self.old!r}, new={self.new!r})"


@dataclass
class DiffResult:
    """Structured result of a dict diff."""

    added: dict[str, Any] = field(default_factory=dict)
    removed: dict[str, Any] = field(default_factory=dict)
    changed: dict[str, Change] = field(default_factory=dict)
    type_changed: dict[str, Change] = field(default_factory=dict)
    children: dict[str, "DiffResult"] = field(default_factory=dict)

    @property
    def is_empty(self) -> bool:
        """True if no differences found."""
        if self.added or self.removed or self.changed or self.type_changed:
            return False
        if not self.children:
            return True
        return all(c.is_empty for c in self.children.values())

    def summary(self) -> dict[str, int]:
        """Return counts of each change type."""
        child_counts = {"added": 0, "removed": 0, "changed": 0, "type_changed": 0}
        for child in self.children.values():
            cs = child.summary()
            for k in child_counts:
                child_counts[k] += cs[k]
        return {
            "added": len(self.added) + child_counts["added"],
            "removed": len(self.removed) + child_counts["removed"],
            "changed": len(self.changed) + child_counts["changed"],
            "type_changed": len(self.type_changed) + child_counts["type_changed"],
        }


def diff(
    old: Any,
    new: Any,
    *,
    set_mode: bool = False,
    ignore_keys: set[str] | None = None,
    float_tolerance: float = 0.0,
) -> DiffResult:
    """Compare two values recursively and return structured diff.

    Args:
        old: The original value (dict, list, or scalar).
        new: The new value to compare against.
        set_mode: If True, compare lists as unordered sets.
        ignore_keys: Set of dict keys to skip during comparison.
        float_tolerance: Tolerance for float comparison (0 = exact).

    Returns:
        DiffResult with added, removed, changed, type_changed, and children.
    """
    if ignore_keys is None:
        ignore_keys = set()

    result = DiffResult()

    # Type change
    if type(old) is not type(new):
        # Special case: int/float are considered compatible numeric types (but not bool)
        if (
            isinstance(old, (int, float))
            and isinstance(new, (int, float))
            and not isinstance(old, bool)
            and not isinstance(new, bool)
        ):
            if _values_equal(old, new, float_tolerance):
                return result  # No difference
            result.changed[""] = Change(old=old, new=new)
            return result
        result.type_changed[""] = Change(old=old, new=new)
        return result

    # Both dicts
    if isinstance(old, dict) and isinstance(new, dict):
        return _diff_dicts(old, new, set_mode=set_mode, ignore_keys=ignore_keys, float_tolerance=float_tolerance)

    # Both lists
    if isinstance(old, list) and isinstance(new, list):
        return _diff_lists(old, new, set_mode=set_mode, float_tolerance=float_tolerance)

    # Scalars
    if not _values_equal(old, new, float_tolerance):
        result.changed[""] = Change(old=old, new=new)

    return result


def _diff_dicts(
    old: dict[str, Any],
    new: dict[str, Any],
    *,
    set_mode: bool = False,
    ignore_keys: set[str],
    float_tolerance: float,
) -> DiffResult:
    """Compare two dicts recursively."""
    result = DiffResult()

    old_keys = set(old.keys()) - ignore_keys
    new_keys = set(new.keys()) - ignore_keys

    # Added keys
    for key in sorted(new_keys - old_keys):
        result.added[key] = new[key]

    # Removed keys
    for key in sorted(old_keys - new_keys):
        result.removed[key] = old[key]

    # Common keys
    for key in sorted(old_keys & new_keys):
        old_val = old[key]
        new_val = new[key]

        # Type change at this key
        if type(old_val) is not type(new_val):
            # int/float compatibility (not bool)
            if (
                isinstance(old_val, (int, float))
                and isinstance(new_val, (int, float))
                and not isinstance(old_val, bool)
                and not isinstance(new_val, bool)
            ):
                if not _values_equal(old_val, new_val, float_tolerance):
                    result.changed[key] = Change(old=old_val, new=new_val)
                continue
            result.type_changed[key] = Change(old=old_val, new=new_val)
            continue

        # Both dicts — recurse
        if isinstance(old_val, dict) and isinstance(new_val, dict):
            child = _diff_dicts(old_val, new_val, set_mode=set_mode, ignore_keys=ignore_keys, float_tolerance=float_tolerance)
            if not child.is_empty:
                result.children[key] = child
            continue

        # Both lists — recurse
        if isinstance(old_val, list) and isinstance(new_val, list):
            child = _diff_lists(old_val, new_val, set_mode=set_mode, float_tolerance=float_tolerance)
            if not child.is_empty:
                result.children[key] = child
            continue

        # Scalars
        if not _values_equal(old_val, new_val, float_tolerance):
            result.changed[key] = Change(old=old_val, new=new_val)

    return result


def _diff_lists(
    old: list[Any],
    new: list[Any],
    *,
    set_mode: bool = False,
    float_tolerance: float = 0.0,
) -> DiffResult:
    """Compare two lists — element-wise or set-based."""
    result = DiffResult()

    if set_mode:
        # Compare as unordered sets using JSON-serializable comparison
        old_set = _make_hashable(old)
        new_set = _make_hashable(new)

        for item in sorted(new_set - old_set, key=_hashable_sort_key):
            result.added[str(len(result.added))] = _unhash(item)

        for item in sorted(old_set - new_set, key=_hashable_sort_key):
            result.removed[str(len(result.removed))] = _unhash(item)

        return result

    # Element-wise comparison (like a dict with integer keys)
    max_len = max(len(old), len(new))

    for i in range(max_len):
        if i >= len(old):
            result.added[str(i)] = new[i]
        elif i >= len(new):
            result.removed[str(i)] = old[i]
        else:
            old_val = old[i]
            new_val = new[i]

            if type(old_val) is not type(new_val):
                if (
                    isinstance(old_val, (int, float))
                    and isinstance(new_val, (int, float))
                    and not isinstance(old_val, bool)
                    and not isinstance(new_val, bool)
                ):
                    if not _values_equal(old_val, new_val, float_tolerance):
                        result.changed[str(i)] = Change(old=old_val, new=new_val)
                    continue
                result.type_changed[str(i)] = Change(old=old_val, new=new_val)
                continue

            if isinstance(old_val, dict) and isinstance(new_val, dict):
                child = _diff_dicts(old_val, new_val, set_mode=set_mode, ignore_keys=set(), float_tolerance=float_tolerance)
                if not child.is_empty:
                    result.children[str(i)] = child
                continue

            if isinstance(old_val, list) and isinstance(new_val, list):
                child = _diff_lists(old_val, new_val, set_mode=set_mode, float_tolerance=float_tolerance)
                if not child.is_empty:
                    result.children[str(i)] = child
                continue

            if not _values_equal(old_val, new_val, float_tolerance):
                result.changed[str(i)] = Change(old=old_val, new=new_val)

    return result


def _values_equal(a: Any, b: Any, tolerance: float = 0.0) -> bool:
    """Compare two scalar values, with optional float tolerance."""
    if isinstance(a, (int, float)) and isinstance(b, (int, float)) and tolerance > 0:
        return abs(float(a) - float(b)) <= tolerance
    return a == b


def _make_hashable(items: list[Any]) -> frozenset:
    """Convert a list to a frozenset of hashable representations for set comparison."""
    result = set()
    for item in items:
        result.add(_to_hashable(item))
    return frozenset(result)


def _to_hashable(item: Any) -> Any:
    """Convert an item to a hashable form for set comparison."""
    if isinstance(item, dict):
        return tuple(sorted((k, _to_hashable(v)) for k, v in item.items()))
    if isinstance(item, list):
        return tuple(_to_hashable(i) for i in item)
    return item


def _unhash(item: Any) -> Any:
    """Convert a hashable representation back to normal form."""
    if isinstance(item, tuple) and all(isinstance(x, tuple) and len(x) == 2 for x in item):
        return {k: _unhash(v) for k, v in item}
    if isinstance(item, tuple):
        return list(_unhash(i) for i in item)
    return item


def _hashable_sort_key(item: Any) -> str:
    """Sort key for hashable items."""
    return str(item)
