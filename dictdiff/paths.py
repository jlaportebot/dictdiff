"""Path filtering — select specific sub-paths of a dict for diffing.

Instead of diffing entire documents, you can focus the diff on a
specific dot-path (e.g. "config.database") to compare only that subtree.
"""

from __future__ import annotations

from typing import Any


def extract_path(data: Any, dot_path: str) -> Any:
    """Extract a value at a dot-path from a nested dict.

    Supports dict key traversal and list index traversal.

    Args:
        data: The root data structure.
        dot_path: Dot-separated path (e.g. "config.db.host" or "items[0].name").

    Returns:
        The value at the specified path.

    Raises:
        KeyError: If a dict key is not found.
        IndexError: If a list index is out of range.
        ValueError: If the path syntax is invalid.
    """
    if not dot_path:
        return data

    tokens = _tokenize_path(dot_path)
    current = data

    for token in tokens:
        if isinstance(current, dict):
            if token not in current:
                raise KeyError(f"Key '{token}' not found at path '{dot_path}'")
            current = current[token]
        elif isinstance(current, list):
            try:
                idx = int(token)
            except ValueError:
                raise ValueError(f"Invalid list index '{token}' at path '{dot_path}'")
            if idx < 0 or idx >= len(current):
                raise IndexError(
                    f"Index {idx} out of range (len={len(current)}) at path '{dot_path}'"
                )
            current = current[idx]
        else:
            raise ValueError(
                f"Cannot traverse into {type(current).__name__} at path '{dot_path}'"
            )

    return current


def set_path(data: dict[str, Any], dot_path: str, value: Any) -> None:
    """Set a value at a dot-path in a nested dict.

    Creates intermediate dicts as needed.

    Args:
        data: The root dict to modify.
        dot_path: Dot-separated path.
        value: The value to set.
    """
    if not dot_path:
        raise ValueError("Cannot set root path")

    tokens = _tokenize_path(dot_path)
    current = data

    for token in tokens[:-1]:
        if token not in current:
            current[token] = {}
        current = current[token]

    current[tokens[-1]] = value


def remove_path(data: dict[str, Any], dot_path: str) -> Any:
    """Remove a value at a dot-path from a nested dict.

    Args:
        data: The root dict to modify.
        dot_path: Dot-separated path.

    Returns:
        The removed value.

    Raises:
        KeyError: If the path doesn't exist.
    """
    if not dot_path:
        raise ValueError("Cannot remove root path")

    tokens = _tokenize_path(dot_path)
    current = data

    for token in tokens[:-1]:
        if not isinstance(current, dict) or token not in current:
            raise KeyError(f"Path '{dot_path}' not found")
        current = current[token]

    if not isinstance(current, dict) or tokens[-1] not in current:
        raise KeyError(f"Path '{dot_path}' not found")

    return current.pop(tokens[-1])


def path_exists(data: Any, dot_path: str) -> bool:
    """Check if a dot-path exists in a nested dict.

    Args:
        data: The root data structure.
        dot_path: Dot-separated path.

    Returns:
        True if the path exists, False otherwise.
    """
    try:
        extract_path(data, dot_path)
        return True
    except (KeyError, IndexError, ValueError):
        return False


def list_paths(data: Any, *, prefix: str = "") -> list[str]:
    """List all dot-paths in a nested dict.

    Args:
        data: The root data structure.
        prefix: Path prefix for recursion.

    Returns:
        List of all dot-paths in the structure.
    """
    paths: list[str] = []

    if isinstance(data, dict):
        for key in sorted(data.keys()):
            current = f"{prefix}.{key}" if prefix else key
            paths.append(current)
            child_paths = list_paths(data[key], prefix=current)
            paths.extend(child_paths)
    elif isinstance(data, list):
        for i, item in enumerate(data):
            current = f"{prefix}[{i}]"
            paths.append(current)
            child_paths = list_paths(item, prefix=current)
            paths.extend(child_paths)

    return paths


def diff_paths(
    old: Any, new: Any, paths: list[str]
) -> dict[str, tuple[Any, Any | None]]:
    """Compare specific paths between two data structures.

    Args:
        old: The original data.
        new: The new data.
        paths: List of dot-paths to compare.

    Returns:
        Dict mapping path to (old_value, new_value) for paths that differ.
        Only includes paths where values differ.
    """
    differences: dict[str, tuple[Any, Any | None]] = {}

    for dot_path in paths:
        old_exists = path_exists(old, dot_path)
        new_exists = path_exists(new, dot_path)

        if old_exists and new_exists:
            old_val = extract_path(old, dot_path)
            new_val = extract_path(new, dot_path)
            if old_val != new_val:
                differences[dot_path] = (old_val, new_val)
        elif old_exists and not new_exists:
            differences[dot_path] = (extract_path(old, dot_path), None)
        elif not old_exists and new_exists:
            differences[dot_path] = (None, extract_path(new, dot_path))

    return differences


def _tokenize_path(dot_path: str) -> list[str]:
    """Tokenize a dot-path into individual keys/indices.

    Handles:
    - Simple keys: "foo" → ["foo"]
    - Dotted paths: "foo.bar" → ["foo", "bar"]
    - List indices: "items[0]" → ["items", "0"]
    - Combined: "items[0].name" → ["items", "0", "name"]

    Args:
        dot_path: The dot-path string.

    Returns:
        List of path tokens.
    """
    tokens: list[str] = []
    current = ""

    i = 0
    while i < len(dot_path):
        ch = dot_path[i]

        if ch == ".":
            if current:
                tokens.append(current)
                current = ""
        elif ch == "[":
            # Save the current key name
            if current:
                tokens.append(current)
                current = ""
            # Read until closing bracket
            i += 1
            bracket_content = ""
            while i < len(dot_path) and dot_path[i] != "]":
                bracket_content += dot_path[i]
                i += 1
            if bracket_content:
                tokens.append(bracket_content)
        elif ch == "]":
            # Skip closing bracket
            pass
        else:
            current += ch

        i += 1

    if current:
        tokens.append(current)

    return tokens
