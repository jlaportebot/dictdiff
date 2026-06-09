"""Merge3 — three-way merge for dicts and lists.

Given a base (ancestor) and two modified versions (ours, theirs),
produce a merged result. Detects conflicts when both sides modified
the same key differently.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from dictdiff.core import DiffResult, diff


@dataclass
class MergeConflict:
    """A conflict where both sides modified the same key differently."""

    key: str
    base_value: Any
    ours_value: Any
    theirs_value: Any

    def __repr__(self) -> str:
        return (
            f"MergeConflict(key={self.key!r}, "
            f"base={self.base_value!r}, "
            f"ours={self.ours_value!r}, "
            f"theirs={self.theirs_value!r})"
        )


@dataclass
class MergeResult:
    """Result of a three-way merge."""

    merged: dict[str, Any] = field(default_factory=dict)
    conflicts: list[MergeConflict] = field(default_factory=list)

    @property
    def has_conflicts(self) -> bool:
        """True if any conflicts were detected."""
        return len(self.conflicts) > 0

    @property
    def conflict_count(self) -> int:
        """Number of conflicts."""
        return len(self.conflicts)

    def summary(self) -> dict[str, Any]:
        """Return a summary of the merge."""
        return {
            "has_conflicts": self.has_conflicts,
            "conflict_count": self.conflict_count,
            "merged_keys": len(self.merged),
            "conflicts": [
                {
                    "key": c.key,
                    "base": c.base_value,
                    "ours": c.ours_value,
                    "theirs": c.theirs_value,
                }
                for c in self.conflicts
            ],
        }


def merge3(
    base: dict[str, Any],
    ours: dict[str, Any],
    theirs: dict[str, Any],
    *,
    ours_wins: bool = True,
    set_mode: bool = False,
    ignore_keys: set[str] | None = None,
    float_tolerance: float = 0.0,
) -> MergeResult:
    """Perform a three-way merge of two dicts against a common base.

    The algorithm:
    1. Compute diff(base, ours) → our_changes
    2. Compute diff(base, theirs) → their_changes
    3. For each key:
       - If unchanged in both → keep base value
       - If changed only in ours → apply ours
       - If changed only in theirs → apply theirs
       - If changed in both to same value → apply (no conflict)
       - If changed in both to different values → conflict

    Args:
        base: The common ancestor dict.
        ours: Our modified version.
        theirs: Their modified version.
        ours_wins: If True, resolve conflicts by taking ours. If False, take theirs.
        set_mode: If True, compare lists as unordered sets.
        ignore_keys: Set of dict keys to skip during comparison.
        float_tolerance: Tolerance for float comparison.

    Returns:
        MergeResult with merged dict and any conflicts.
    """
    if ignore_keys is None:
        ignore_keys = set()

    result = MergeResult()

    our_changes = diff(
        base,
        ours,
        set_mode=set_mode,
        ignore_keys=ignore_keys,
        float_tolerance=float_tolerance,
    )
    their_changes = diff(
        base,
        theirs,
        set_mode=set_mode,
        ignore_keys=ignore_keys,
        float_tolerance=float_tolerance,
    )

    # Collect all keys from all three dicts
    all_keys = set(base.keys()) | set(ours.keys()) | set(theirs.keys())
    all_keys -= ignore_keys

    for key in sorted(all_keys):
        base_val = base.get(key, _MISSING)
        ours_val = ours.get(key, _MISSING)
        theirs_val = theirs.get(key, _MISSING)

        _merge_key(
            key=key,
            base_val=base_val,
            ours_val=ours_val,
            theirs_val=theirs_val,
            our_changes=our_changes,
            their_changes=their_changes,
            result=result,
            ours_wins=ours_wins,
            set_mode=set_mode,
            ignore_keys=ignore_keys,
            float_tolerance=float_tolerance,
        )

    return result


def _merge_key(
    *,
    key: str,
    base_val: Any,
    ours_val: Any,
    theirs_val: Any,
    our_changes: DiffResult,
    their_changes: DiffResult,
    result: MergeResult,
    ours_wins: bool,
    set_mode: bool,
    ignore_keys: set[str],
    float_tolerance: float,
) -> None:
    """Merge a single key from base, ours, theirs."""
    # Check if ours modified this key
    ours_changed_key = _key_was_changed(our_changes, key)
    theirs_changed_key = _key_was_changed(their_changes, key)

    # Neither side changed → keep base value
    if not ours_changed_key and not theirs_changed_key:
        if base_val is not _MISSING:
            result.merged[key] = base_val
        return

    # Only ours changed
    if ours_changed_key and not theirs_changed_key:
        if ours_val is not _MISSING:
            result.merged[key] = ours_val
        # If ours deleted the key, it's not in merged
        return

    # Only theirs changed
    if not ours_changed_key and theirs_changed_key:
        if theirs_val is not _MISSING:
            result.merged[key] = theirs_val
        return

    # Both changed — check if they agree
    if ours_val is _MISSING and theirs_val is _MISSING:
        # Both deleted → agree
        return

    if ours_val is not _MISSING and theirs_val is not _MISSING:
        # Both present — check if values are equal
        if _values_agree(ours_val, theirs_val, float_tolerance=float_tolerance):
            result.merged[key] = ours_val
            return

        # Both dicts → try recursive merge
        if (
            isinstance(ours_val, dict)
            and isinstance(theirs_val, dict)
            and isinstance(base_val, dict)
            if base_val is not _MISSING
            else False
        ):
            child_result = merge3(
                base_val,
                ours_val,
                theirs_val,
                ours_wins=ours_wins,
                set_mode=set_mode,
                ignore_keys=ignore_keys,
                float_tolerance=float_tolerance,
            )
            result.merged[key] = child_result.merged
            # Prefix conflicts with parent key
            for conflict in child_result.conflicts:
                result.conflicts.append(
                    MergeConflict(
                        key=f"{key}.{conflict.key}",
                        base_value=conflict.base_value,
                        ours_value=conflict.ours_value,
                        theirs_value=conflict.theirs_value,
                    )
                )
            return

        # Conflict — different values
        resolved = ours_val if ours_wins else theirs_val
        result.merged[key] = resolved
        result.conflicts.append(
            MergeConflict(
                key=key,
                base_value=base_val if base_val is not _MISSING else None,
                ours_value=ours_val,
                theirs_value=theirs_val,
            )
        )
        return

    # One deleted, one modified — conflict
    if ours_val is _MISSING:
        # Ours deleted, theirs modified
        resolved = theirs_val if not ours_wins else None
        if resolved is not None:
            result.merged[key] = resolved
        result.conflicts.append(
            MergeConflict(
                key=key,
                base_value=base_val if base_val is not _MISSING else None,
                ours_value=None,
                theirs_value=theirs_val,
            )
        )
        return

    if theirs_val is _MISSING:
        # Theirs deleted, ours modified
        resolved = ours_val if ours_wins else None
        if resolved is not None:
            result.merged[key] = resolved
        result.conflicts.append(
            MergeConflict(
                key=key,
                base_value=base_val if base_val is not _MISSING else None,
                ours_value=ours_val,
                theirs_value=None,
            )
        )


def _key_was_changed(change_result: DiffResult, key: str) -> bool:
    """Check if a key appears in any change category."""
    return (
        key in change_result.added
        or key in change_result.removed
        or key in change_result.changed
        or key in change_result.type_changed
        or key in change_result.children
    )


def _values_agree(a: Any, b: Any, *, float_tolerance: float = 0.0) -> bool:
    """Check if two values are effectively equal."""
    if type(a) is not type(b):
        # int/float compatibility
        if (
            isinstance(a, (int, float))
            and isinstance(b, (int, float))
            and not isinstance(a, bool)
            and not isinstance(b, bool)
        ):
            if float_tolerance > 0:
                return abs(float(a) - float(b)) <= float_tolerance
            return float(a) == float(b)
        return False
    if isinstance(a, dict) and isinstance(b, dict):
        if set(a.keys()) != set(b.keys()):
            return False
        return all(
            _values_agree(a[k], b[k], float_tolerance=float_tolerance) for k in a
        )
    if isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            return False
        return all(
            _values_agree(x, y, float_tolerance=float_tolerance) for x, y in zip(a, b)
        )
    if (
        isinstance(a, (int, float))
        and isinstance(b, (int, float))
        and float_tolerance > 0
    ):
        return abs(float(a) - float(b)) <= float_tolerance
    return a == b


class _MissingSentinel:
    """Sentinel value to distinguish 'key not present' from 'value is None'."""

    def __repr__(self) -> str:
        return "<MISSING>"


_MISSING = _MissingSentinel()
