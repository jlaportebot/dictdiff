"""LCS-based list diff — find the longest common subsequence and produce
an edit script (insert/delete) to transform old list into new list.

This is much more useful than element-wise comparison for lists where
items can be reordered, inserted, or deleted.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from dictdiff.core import Change, DiffResult


@dataclass
class EditOp:
    """A single edit operation in a list edit script."""

    op: str  # "equal", "insert", "delete"
    old_idx: int | None = None
    new_idx: int | None = None
    old_value: Any = None
    new_value: Any = None

    def __repr__(self) -> str:
        if self.op == "equal":
            return f"Equal({self.old_value!r} @ [{self.old_idx}])"
        if self.op == "insert":
            return f"Insert({self.new_value!r} @ [{self.new_idx}])"
        if self.op == "delete":
            return f"Delete({self.old_value!r} @ [{self.old_idx}])"
        return f"EditOp({self.op!r})"


@dataclass
class EditScript:
    """A sequence of edit operations to transform one list into another."""

    ops: list[EditOp] = field(default_factory=list)

    @property
    def inserts(self) -> list[EditOp]:
        """Return only insert operations."""
        return [op for op in self.ops if op.op == "insert"]

    @property
    def deletes(self) -> list[EditOp]:
        """Return only delete operations."""
        return [op for op in self.ops if op.op == "delete"]

    @property
    def equals(self) -> list[EditOp]:
        """Return only equal operations."""
        return [op for op in self.ops if op.op == "equal"]

    @property
    def distance(self) -> int:
        """Edit distance (number of insertions + deletions)."""
        return len(self.inserts) + len(self.deletes)

    def apply(self, old: list[Any]) -> list[Any]:
        """Apply this edit script to transform old list into new list."""
        result: list[Any] = []
        for op in self.ops:
            if op.op == "equal":
                result.append(old[op.old_idx])  # type: ignore[index]
            elif op.op == "insert":
                result.append(op.new_value)
            # delete ops are skipped — items removed from output
        return result

    def summary(self) -> dict[str, int]:
        """Return counts of each operation type."""
        return {
            "equal": len(self.equals),
            "insert": len(self.inserts),
            "delete": len(self.deletes),
            "distance": self.distance,
        }


def lcs_length(old: list[Any], new: list[Any]) -> int:
    """Compute the length of the longest common subsequence.

    Uses the classic DP algorithm with O(n*m) time and space.
    """
    n = len(old)
    m = len(new)

    # Build DP table
    dp = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            if _items_equal(old[i - 1], new[j - 1]):
                dp[i][j] = dp[i - 1][j - 1] + 1
            else:
                dp[i][j] = max(dp[i - 1][j], dp[i][j - 1])

    return dp[n][m]


def compute_lcs(old: list[Any], new: list[Any]) -> list[tuple[int, int]]:
    """Compute the LCS as a list of (old_idx, new_idx) pairs.

    Returns aligned indices of the longest common subsequence.
    """
    n = len(old)
    m = len(new)

    # Build DP table
    dp = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            if _items_equal(old[i - 1], new[j - 1]):
                dp[i][j] = dp[i - 1][j - 1] + 1
            else:
                dp[i][j] = max(dp[i - 1][j], dp[i][j - 1])

    # Backtrack to find the actual LCS
    matches: list[tuple[int, int]] = []
    i, j = n, m
    while i > 0 and j > 0:
        if _items_equal(old[i - 1], new[j - 1]):
            matches.append((i - 1, j - 1))
            i -= 1
            j -= 1
        elif dp[i - 1][j] >= dp[i][j - 1]:
            i -= 1
        else:
            j -= 1

    matches.reverse()
    return matches


def diff_lcs(old: list[Any], new: list[Any]) -> EditScript:
    """Compute an edit script using LCS to transform old list into new list.

    This produces a more intelligent diff than element-wise comparison,
    correctly handling insertions and deletions in the middle of lists.

    Args:
        old: The original list.
        new: The new list.

    Returns:
        EditScript with the sequence of operations.
    """
    matches = compute_lcs(old, new)
    script = EditScript()

    old_i = 0
    new_j = 0

    for match_old, match_new in matches:
        # Delete items before this match in old
        while old_i < match_old:
            script.ops.append(EditOp(op="delete", old_idx=old_i, old_value=old[old_i]))
            old_i += 1

        # Insert items before this match in new
        while new_j < match_new:
            script.ops.append(EditOp(op="insert", new_idx=new_j, new_value=new[new_j]))
            new_j += 1

        # Equal item
        script.ops.append(EditOp(op="equal", old_idx=old_i, new_idx=new_j, old_value=old[old_i], new_value=new[new_j]))
        old_i += 1
        new_j += 1

    # Remaining deletions
    while old_i < len(old):
        script.ops.append(EditOp(op="delete", old_idx=old_i, old_value=old[old_i]))
        old_i += 1

    # Remaining insertions
    while new_j < len(new):
        script.ops.append(EditOp(op="insert", new_idx=new_j, new_value=new[new_j]))
        new_j += 1

    return script


def diff_lcs_to_diff_result(old: list[Any], new: list[Any]) -> DiffResult:
    """Compute LCS-based list diff and convert to DiffResult format.

    This provides compatibility with the existing DiffResult-based API
    while using smarter list comparison internally.

    Args:
        old: The original list.
        new: The new list.

    Returns:
        DiffResult with added/removed items from LCS analysis.
    """
    script = diff_lcs(old, new)
    result = DiffResult()

    for op in script.inserts:
        result.added[str(op.new_idx)] = op.new_value

    for op in script.deletes:
        result.removed[str(op.old_idx)] = op.old_value

    return result


def _items_equal(a: Any, b: Any) -> bool:
    """Compare two items for LCS matching.

    For dicts, uses a simplified deep equality check.
    For scalars, uses direct comparison.
    """
    if type(a) is not type(b):
        return False
    if isinstance(a, dict) and isinstance(b, dict):
        return _dicts_equal(a, b)
    if isinstance(a, list) and isinstance(b, list):
        return _lists_equal(a, b)
    return a == b


def _dicts_equal(a: dict[str, Any], b: dict[str, Any]) -> bool:
    """Deep dict equality for LCS comparison."""
    if set(a.keys()) != set(b.keys()):
        return False
    for key in a:
        if not _items_equal(a[key], b[key]):
            return False
    return True


def _lists_equal(a: list[Any], b: list[Any]) -> bool:
    """Deep list equality for LCS comparison."""
    if len(a) != len(b):
        return False
    for x, y in zip(a, b):
        if not _items_equal(x, y):
            return False
    return True
