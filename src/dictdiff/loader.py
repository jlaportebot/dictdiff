"""File loading logic for dictdiff — supports JSON, YAML, and TOML."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml


def _load_json(path: Path) -> dict[str, Any]:
    with path.open() as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError(
            f"Expected a JSON object (dict) in {path}, got {type(data).__name__}"
        )
    return data


def _load_yaml(path: Path) -> dict[str, Any]:
    with path.open() as f:
        data = yaml.safe_load(f)
    if data is None:
        return {}
    if not isinstance(data, dict):
        raise ValueError(
            f"Expected a YAML mapping in {path}, got {type(data).__name__}"
        )
    return data


def _load_toml(path: Path) -> dict[str, Any]:
    try:
        if hasattr(__import__("tomllib"), "load"):
            import tomllib
        else:
            import tomli as tomllib  # type: ignore[no-redef]
    except ImportError:
        raise ImportError(
            "TOML support requires Python 3.11+ or the 'toml' extra: pip install dictdiff[toml]"
        )
    with path.open("rb") as f:
        data = tomllib.load(f)
    if not isinstance(data, dict):
        raise ValueError(f"Expected a TOML table in {path}, got {type(data).__name__}")
    return data


_LOADERS: dict[str, type] = {}  # filled by _register_loaders


def _register_loaders() -> None:
    _LOADERS[".json"] = _load_json
    _LOADERS[".yaml"] = _load_yaml
    _LOADERS[".yml"] = _load_yaml
    _LOADERS[".toml"] = _load_toml


_register_loaders()


def load_file(path: str | Path) -> dict[str, Any]:
    """Load a file and return its contents as a dict.

    Format is detected by extension: .json, .yaml/.yml, .toml.
    """
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"File not found: {p}")
    if not p.is_file():
        raise ValueError(f"Not a file: {p}")

    suffix = p.suffix.lower()
    loader = _LOADERS.get(suffix)
    if loader is None:
        raise ValueError(
            f"Unsupported format '{suffix}'. Supported: {', '.join(sorted(_LOADERS))}"
        )
    return loader(p)
