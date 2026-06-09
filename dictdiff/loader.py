"""Loader — unified file loading for JSON, YAML, TOML, INI, and Python dict files.

Provides a single entry point for loading any supported format,
with automatic format detection based on file extension.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import json


class LoaderError(Exception):
    """Raised when a file cannot be loaded."""

    def __init__(self, path: str | Path, message: str) -> None:
        self.path = str(path)
        self.message = message
        super().__init__(f"{path}: {message}")


def load_file(path: str | Path) -> Any:
    """Load a data file (JSON, YAML, TOML, INI, or Python dict).

    Format is detected from the file extension:
    - .json → JSON
    - .yaml, .yml → YAML (requires pyyaml)
    - .toml → TOML (requires Python 3.11+ or tomli)
    - .ini, .cfg → INI config (uses configparser)
    - .py → Python dict file
    - Other → tries JSON as default

    Args:
        path: Path to the file.

    Returns:
        Parsed data (usually dict or list).

    Raises:
        LoaderError: If the file cannot be loaded.
        FileNotFoundError: If the file doesn't exist.
    """
    p = Path(path)

    if not p.exists():
        raise FileNotFoundError(f"File not found: {path}")

    suffix = p.suffix.lower()

    try:
        if suffix == ".json":
            return _load_json(p)
        elif suffix in (".yaml", ".yml"):
            return _load_yaml(p)
        elif suffix == ".toml":
            return _load_toml(p)
        elif suffix in (".ini", ".cfg"):
            return _load_ini(p)
        elif suffix == ".py":
            return _load_python(p)
        else:
            # Default: try JSON
            return _load_json(p)
    except LoaderError:
        raise
    except FileNotFoundError:
        raise
    except Exception as e:
        raise LoaderError(path, f"Failed to parse {suffix} file: {e}") from e


def load_string(content: str, *, format: str = "json") -> Any:
    """Load data from a string in the specified format.

    Args:
        content: The string content to parse.
        format: The format — "json", "yaml", "toml".

    Returns:
        Parsed data.
    """
    try:
        if format == "json":
            return json.loads(content)
        elif format in ("yaml", "yml"):
            import yaml

            return yaml.safe_load(content)
        elif format == "toml":
            try:
                import tomllib
            except ImportError:
                import tomli as tomllib  # type: ignore[no-redef]
            return tomllib.loads(content)
        else:
            raise ValueError(f"Unsupported format: {format}")
    except ValueError:
        raise
    except Exception as e:
        raise LoaderError("<string>", f"Failed to parse {format} string: {e}") from e


def detect_format(path: str | Path) -> str:
    """Detect file format from extension.

    Args:
        path: File path.

    Returns:
        Format name: "json", "yaml", "toml", "ini", "python", or "unknown".
    """
    suffix = Path(path).suffix.lower()
    format_map = {
        ".json": "json",
        ".yaml": "yaml",
        ".yml": "yaml",
        ".toml": "toml",
        ".ini": "ini",
        ".cfg": "ini",
        ".py": "python",
    }
    return format_map.get(suffix, "unknown")


def _load_json(path: Path) -> Any:
    """Load a JSON file."""
    return json.loads(path.read_text(encoding="utf-8"))


def _load_yaml(path: Path) -> Any:
    """Load a YAML file."""
    try:
        import yaml
    except ImportError:
        raise LoaderError(
            path,
            "YAML support requires 'pyyaml' package. Install with: pip install pyyaml",
        )
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _load_toml(path: Path) -> Any:
    """Load a TOML file."""
    try:
        import tomllib
    except ImportError:
        try:
            import tomli as tomllib  # type: ignore[no-redef]
        except ImportError:
            raise LoaderError(
                path,
                "TOML support requires Python 3.11+ or 'tomli' package. Install with: pip install tomli",
            )
    return tomllib.loads(path.read_text(encoding="utf-8"))


def _load_ini(path: Path) -> dict[str, Any]:
    """Load an INI config file as a dict."""
    import configparser

    parser = configparser.ConfigParser()
    parser.read_string(path.read_text(encoding="utf-8"))

    result: dict[str, Any] = {}
    for section in parser.sections():
        result[section] = dict(parser.items(section))

    # Include DEFAULT section items if any
    defaults = dict(parser.defaults())
    if defaults:
        result["DEFAULT"] = defaults

    return result


def _load_python(path: Path) -> Any:
    """Load a Python dict from a .py file."""
    namespace: dict[str, Any] = {"__builtins__": {}}
    code = path.read_text(encoding="utf-8")
    exec(compile(code, str(path), "exec"), namespace)  # noqa: S102

    # Find the first dict value in the namespace (skip __builtins__)
    for key, value in namespace.items():
        if key.startswith("__"):
            continue
        if isinstance(value, dict):
            return value

    raise LoaderError(path, "No dict found in Python file")
