"""Core diffing logic for dictdiff."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ChangeKind(Enum):
    """What kind of change occurred at a key path."""

    ADDED = "added"
    REMOVED = "removed"
    TYPE_CHANGED = "type_changed"
    VALUE_CHANGED = "value_changed"
    UNCHANGED = "unchanged"


@dataclass
class DiffEntry:
    """A single difference between two dicts at a given key path."""

    path: str
    kind: ChangeKind
    old_value: Any = field(default=None)
    new_value: Any = field(default=None)
    old_type: str = field(default="")
    new_type: str = field(default="")
    children: list[DiffEntry] = field(default_factory=list)

    @property
    def is_leaf(self) -> bool:
        return not self.children


def _type_name(val: Any) -> str:
    if val is None:
        return "null"
    if isinstance(val, bool):
        return "bool"
    if isinstance(val, int):
        return "int"
    if isinstance(val, float):
        return "float"
    if isinstance(val, str):
        return "str"
    if isinstance(val, list):
        return "list"
    if isinstance(val, dict):
        return "dict"
    return type(val).__name__


def _values_equal(a: Any, b: Any) -> bool:
    """Deep equality check that handles lists and dicts."""
    if type(a) is not type(b):
        return False
    if isinstance(a, dict):
        if a.keys() != b.keys():
            return False
        return all(_values_equal(a[k], b[k]) for k in a)
    if isinstance(a, list):
        if len(a) != len(b):
            return False
        return all(_values_equal(x, y) for x, y in zip(a, b))
    return a == b


def diff_dicts(old: dict[str, Any], new: dict[str, Any], path: str = "") -> list[DiffEntry]:
    """Recursively diff two dicts and return a list of DiffEntry objects.

    Only returns entries that represent actual changes (kind != UNCHANGED),
    unless the entry has changed children.
    """
    results: list[DiffEntry] = []
    all_keys = sorted(set(old.keys()) | set(new.keys()))

    for key in all_keys:
        key_path = f"{path}.{key}" if path else key
        in_old = key in old
        in_new = key in new

        if in_old and not in_new:
            results.append(DiffEntry(path=key_path, kind=ChangeKind.REMOVED, old_value=old[key]))
            continue

        if not in_old and in_new:
            results.append(DiffEntry(path=key_path, kind=ChangeKind.ADDED, new_value=new[key]))
            continue

        old_val = old[key]
        new_val = new[key]
        old_t = _type_name(old_val)
        new_t = _type_name(new_val)

        if old_t != new_t:
            results.append(
                DiffEntry(
                    path=key_path,
                    kind=ChangeKind.TYPE_CHANGED,
                    old_value=old_val,
                    new_value=new_val,
                    old_type=old_t,
                    new_type=new_t,
                )
            )
            continue

        if isinstance(old_val, dict) and isinstance(new_val, dict):
            child_diffs = diff_dicts(old_val, new_val, key_path)
            if child_diffs:
                results.append(
                    DiffEntry(
                        path=key_path,
                        kind=ChangeKind.UNCHANGED,
                        children=child_diffs,
                    )
                )
            continue

        if isinstance(old_val, list) and isinstance(new_val, list):
            if _values_equal(old_val, new_val):
                continue
            results.append(
                DiffEntry(
                    path=key_path,
                    kind=ChangeKind.VALUE_CHANGED,
                    old_value=old_val,
                    new_value=new_val,
                )
            )
            continue

        if old_val != new_val:
            results.append(
                DiffEntry(
                    path=key_path,
                    kind=ChangeKind.VALUE_CHANGED,
                    old_value=old_val,
                    new_value=new_val,
                )
            )

    return results


def count_changes(entries: list[DiffEntry]) -> dict[str, int]:
    """Count changes by kind across all entries (recursive)."""
    counts = {k.value: 0 for k in ChangeKind if k != ChangeKind.UNCHANGED}
    for entry in entries:
        if entry.kind != ChangeKind.UNCHANGED:
            counts[entry.kind.value] += 1
        if entry.children:
            child_counts = count_changes(entry.children)
            for k, v in child_counts.items():
                counts[k] += v
    return counts


def flatten(entries: list[DiffEntry]) -> list[DiffEntry]:
    """Flatten nested diff entries into a flat list of leaf changes."""
    flat: list[DiffEntry] = []
    for entry in entries:
        if entry.children:
            flat.extend(flatten(entry.children))
        elif entry.kind != ChangeKind.UNCHANGED:
            flat.append(entry)
    return flat
