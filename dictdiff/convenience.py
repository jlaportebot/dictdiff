"""Convenience functions for common diff operations."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from dictdiff.core import DiffResult, diff
from dictdiff.patch import generate_patch
from dictdiff.loader import load_file, load_string, detect_format
from dictdiff.ignore import IgnoreMatcher, filter_dict


def diff_files(
    old_path: str | Path,
    new_path: str | Path,
    *,
    set_mode: bool = False,
    ignore_keys: set[str] | None = None,
    float_tolerance: float = 0.0,
    lcs_mode: bool = False,
    ignore_patterns: list[str] | None = None,
) -> DiffResult:
    """Compare two data files and return a DiffResult.

    Supports JSON, YAML, TOML, INI, and Python dict files.

    Args:
        old_path: Path to the original file.
        new_path: Path to the new file.
        set_mode: If True, compare lists as unordered sets.
        ignore_keys: Set of dict keys to skip during comparison.
        float_tolerance: Tolerance for float comparison.
        lcs_mode: If True, use LCS-based list comparison.
        ignore_patterns: List of ignore patterns (glob/regex/exact/dotpath).

    Returns:
        DiffResult with structured differences.
    """
    old_data = load_file(old_path)
    new_data = load_file(new_path)

    # Apply ignore patterns if provided
    if ignore_patterns:
        matcher = IgnoreMatcher.from_patterns(ignore_patterns)
        old_data = filter_dict(old_data, matcher) if isinstance(old_data, dict) else old_data
        new_data = filter_dict(new_data, matcher) if isinstance(new_data, dict) else new_data

    return diff(
        old_data, new_data,
        set_mode=set_mode,
        ignore_keys=ignore_keys,
        float_tolerance=float_tolerance,
        lcs_mode=lcs_mode,
    )


def diff_strings(
    old_json: str,
    new_json: str,
    *,
    set_mode: bool = False,
    ignore_keys: set[str] | None = None,
    float_tolerance: float = 0.0,
    lcs_mode: bool = False,
    format: str = "json",
) -> DiffResult:
    """Compare two data strings and return a DiffResult.

    Args:
        old_json: Original data string.
        new_json: New data string.
        set_mode: If True, compare lists as unordered sets.
        ignore_keys: Set of dict keys to skip during comparison.
        float_tolerance: Tolerance for float comparison.
        lcs_mode: If True, use LCS-based list comparison.
        format: Input format — "json", "yaml", or "toml".

    Returns:
        DiffResult with structured differences.
    """
    old_data = load_string(old_json, format=format)
    new_data = load_string(new_json, format=format)
    return diff(
        old_data, new_data,
        set_mode=set_mode,
        ignore_keys=ignore_keys,
        float_tolerance=float_tolerance,
        lcs_mode=lcs_mode,
    )


def diff_to_patch(
    old: Any,
    new: Any,
    *,
    set_mode: bool = False,
    ignore_keys: set[str] | None = None,
    float_tolerance: float = 0.0,
    lcs_mode: bool = False,
) -> list[dict[str, Any]]:
    """Compare two values and return an RFC 6902 JSON Patch.

    Combines diff() and generate_patch() in one call.

    Args:
        old: The original value.
        new: The new value.
        set_mode: If True, compare lists as unordered sets.
        ignore_keys: Set of dict keys to skip during comparison.
        float_tolerance: Tolerance for float comparison.
        lcs_mode: If True, use LCS-based list comparison.

    Returns:
        List of RFC 6902 patch operations.
    """
    result = diff(
        old, new,
        set_mode=set_mode,
        ignore_keys=ignore_keys,
        float_tolerance=float_tolerance,
        lcs_mode=lcs_mode,
    )
    return generate_patch(result)
