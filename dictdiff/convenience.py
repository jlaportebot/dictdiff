"""Convenience functions for common diff operations."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from dictdiff.core import DiffResult, diff
from dictdiff.patch import generate_patch


def diff_files(
    old_path: str | Path,
    new_path: str | Path,
    *,
    set_mode: bool = False,
    ignore_keys: set[str] | None = None,
    float_tolerance: float = 0.0,
) -> DiffResult:
    """Compare two JSON files and return a DiffResult.

    Args:
        old_path: Path to the original JSON file.
        new_path: Path to the new JSON file.
        set_mode: If True, compare lists as unordered sets.
        ignore_keys: Set of dict keys to skip during comparison.
        float_tolerance: Tolerance for float comparison.

    Returns:
        DiffResult with structured differences.
    """
    old_data = _load_json(old_path)
    new_data = _load_json(new_path)
    return diff(old_data, new_data, set_mode=set_mode, ignore_keys=ignore_keys, float_tolerance=float_tolerance)


def diff_strings(
    old_json: str,
    new_json: str,
    *,
    set_mode: bool = False,
    ignore_keys: set[str] | None = None,
    float_tolerance: float = 0.0,
) -> DiffResult:
    """Compare two JSON strings and return a DiffResult.

    Args:
        old_json: Original JSON string.
        new_json: New JSON string.
        set_mode: If True, compare lists as unordered sets.
        ignore_keys: Set of dict keys to skip during comparison.
        float_tolerance: Tolerance for float comparison.

    Returns:
        DiffResult with structured differences.
    """
    old_data = json.loads(old_json)
    new_data = json.loads(new_json)
    return diff(old_data, new_data, set_mode=set_mode, ignore_keys=ignore_keys, float_tolerance=float_tolerance)


def diff_to_patch(
    old: Any,
    new: Any,
    *,
    set_mode: bool = False,
    ignore_keys: set[str] | None = None,
    float_tolerance: float = 0.0,
) -> list[dict[str, Any]]:
    """Compare two values and return an RFC 6902 JSON Patch.

    Combines diff() and generate_patch() in one call.

    Args:
        old: The original value.
        new: The new value.
        set_mode: If True, compare lists as unordered sets.
        ignore_keys: Set of dict keys to skip during comparison.
        float_tolerance: Tolerance for float comparison.

    Returns:
        List of RFC 6902 patch operations.
    """
    result = diff(old, new, set_mode=set_mode, ignore_keys=ignore_keys, float_tolerance=float_tolerance)
    return generate_patch(result)


def _load_json(path: str | Path) -> Any:
    """Load a JSON file."""
    p = Path(path)
    return json.loads(p.read_text(encoding="utf-8"))
