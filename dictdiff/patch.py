"""Patch generation — produce RFC 6902 JSON Patch from a DiffResult."""

from __future__ import annotations

from typing import Any

from dictdiff.core import Change, DiffResult


def generate_patch(result: DiffResult, path: str = "") -> list[dict[str, Any]]:
    """Generate an RFC 6902 JSON Patch from a DiffResult.

    Operations:
    - "add" for new keys/values
    - "remove" for deleted keys/values
    - "replace" for changed values and type changes

    Args:
        result: The DiffResult to convert.
        path: Current JSON Pointer path ( e.g. "/foo/bar" ).

    Returns:
        List of RFC 6902 patch operations.
    """
    ops: list[dict[str, Any]] = []

    # Removed keys
    for key, _ in result.removed.items():
        ops.append({"op": "remove", "path": f"{path}/{_escape(key)}"})

    # Added keys
    for key, value in result.added.items():
        ops.append({"op": "add", "path": f"{path}/{_escape(key)}", "value": value})

    # Changed values
    for key, change in result.changed.items():
        ops.append({"op": "replace", "path": f"{path}/{_escape(key)}", "value": change.new})

    # Type changes
    for key, change in result.type_changed.items():
        ops.append({"op": "replace", "path": f"{path}/{_escape(key)}", "value": change.new})

    # Recurse into children
    for key, child in result.children.items():
        ops.extend(generate_patch(child, path=f"{path}/{_escape(key)}"))

    return ops


def apply_patch(doc: Any, patch_ops: list[dict[str, Any]]) -> Any:
    """Apply RFC 6902 JSON Patch operations to a document.

    Supports: add, remove, replace.

    Args:
        doc: The original document.
        patch_ops: List of RFC 6902 operations.

    Returns:
        The patched document.
    """
    import copy

    doc = copy.deepcopy(doc)

    for op in patch_ops:
        operation = op["op"]
        path = op["path"]

        if operation == "add":
            _apply_add(doc, path, op["value"])
        elif operation == "remove":
            _apply_remove(doc, path)
        elif operation == "replace":
            _apply_replace(doc, path, op["value"])
        else:
            raise ValueError(f"Unsupported operation: {operation}")

    return doc


def _escape(key: str) -> str:
    """Escape a JSON Pointer token per RFC 6901."""
    return key.replace("~", "~0").replace("/", "~1")


def _unescape(token: str) -> str:
    """Unescape a JSON Pointer token per RFC 6901."""
    return token.replace("~1", "/").replace("~0", "~")


def _parse_path(path: str) -> list[str]:
    """Parse a JSON Pointer path into tokens."""
    if not path:
        return []
    if path == "/":
        return [""]
    parts = path.split("/")
    if parts[0] != "":
        raise ValueError(f"Invalid JSON Pointer: {path}")
    return [_unescape(p) for p in parts[1:]]


def _navigate(doc: Any, tokens: list[str]) -> tuple[Any, str]:
    """Navigate to the parent of the target, returning (parent, final_key)."""
    current = doc
    for token in tokens[:-1]:
        if isinstance(current, dict):
            current = current[token]
        elif isinstance(current, list):
            current = current[int(token)]
        else:
            raise ValueError(f"Cannot navigate through {type(current)}")

    return current, tokens[-1]


def _apply_add(doc: Any, path: str, value: Any) -> None:
    """Apply an 'add' operation."""
    tokens = _parse_path(path)
    if not tokens:
        raise ValueError("Cannot add to root path")

    parent, key = _navigate(doc, tokens)

    if isinstance(parent, dict):
        parent[key] = value
    elif isinstance(parent, list):
        if key == "-":
            parent.append(value)
        else:
            idx = int(key)
            parent.insert(idx, value)


def _apply_remove(doc: Any, path: str) -> None:
    """Apply a 'remove' operation."""
    tokens = _parse_path(path)
    if not tokens:
        raise ValueError("Cannot remove root path")

    parent, key = _navigate(doc, tokens)

    if isinstance(parent, dict):
        del parent[key]
    elif isinstance(parent, list):
        del parent[int(key)]


def _apply_replace(doc: Any, path: str, value: Any) -> None:
    """Apply a 'replace' operation."""
    tokens = _parse_path(path)
    if not tokens:
        raise ValueError("Cannot replace root path")

    parent, key = _navigate(doc, tokens)

    if isinstance(parent, dict):
        parent[key] = value
    elif isinstance(parent, list):
        parent[int(key)] = value
