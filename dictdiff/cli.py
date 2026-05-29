"""CLI entry point for dictdiff."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import click

from dictdiff.core import DiffResult, diff
from dictdiff.formatter import format_diff, format_table, format_unified
from dictdiff.patch import generate_patch


@click.command(context_settings={"help_option_names": ["-h", "--help"]})
@click.argument("old_file", type=click.Path(exists=False))
@click.argument("new_file", type=click.Path(exists=False))
@click.option("--set-mode", is_flag=True, default=False, help="Compare lists as unordered sets.")
@click.option("--patch", "output_patch", is_flag=True, default=False, help="Output RFC 6902 JSON Patch.")
@click.option("--ignore", multiple=True, help="Keys to ignore during comparison (repeatable).")
@click.option("--float-tolerance", type=float, default=0.0, help="Tolerance for float comparison.")
@click.option("--format", "fmt", type=click.Choice(["tree", "table", "unified", "json"]), default="tree", help="Output format.")
@click.option("--quiet", "-q", is_flag=True, default=False, help="Only set exit code, no output.")
@click.version_option(version="0.1.0")
def main(
    old_file: str,
    new_file: str,
    set_mode: bool,
    output_patch: bool,
    ignore: tuple[str, ...],
    float_tolerance: float,
    fmt: str,
    quiet: bool,
) -> None:
    """Compare two JSON/YAML/Python dict files semantically.

    OLD_FILE and NEW_FILE can be JSON (.json), YAML (.yaml/.yml),
    or Python dict (.py) files. Use '-' for stdin.
    """
    try:
        old_data = _load_file(old_file)
        new_data = _load_file(new_file)
    except Exception as e:
        click.echo(f"Error loading files: {e}", err=True)
        sys.exit(2)

    ignore_keys = set(ignore) if ignore else None

    result = diff(old_data, new_data, set_mode=set_mode, ignore_keys=ignore_keys, float_tolerance=float_tolerance)

    if quiet:
        sys.exit(0 if result.is_empty else 1)

    if output_patch:
        patch_ops = generate_patch(result)
        click.echo(json.dumps(patch_ops, indent=2))
    elif fmt == "tree":
        format_diff(result)
    elif fmt == "table":
        format_table(result)
    elif fmt == "unified":
        output = format_unified(result)
        if output:
            click.echo(output)
    elif fmt == "json":
        click.echo(json.dumps(_result_to_json(result), indent=2))

    sys.exit(0 if result.is_empty else 1)


def _load_file(path: str) -> Any:
    """Load a JSON, YAML, or Python dict file."""
    if path == "-":
        return json.load(sys.stdin)

    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"File not found: {path}")

    suffix = p.suffix.lower()

    if suffix == ".json":
        return json.loads(p.read_text(encoding="utf-8"))
    elif suffix in (".yaml", ".yml"):
        try:
            import yaml
        except ImportError:
            click.echo("YAML support requires 'pyyaml' package. Install with: pip install pyyaml", err=True)
            sys.exit(2)
        return yaml.safe_load(p.read_text(encoding="utf-8"))
    elif suffix == ".py":
        # Load Python dict from file
        namespace: dict[str, Any] = {}
        exec(compile(p.read_text(encoding="utf-8"), path, "exec"), namespace)  # noqa: S102
        # Find the first dict value in the namespace
        for v in namespace.values():
            if isinstance(v, dict):
                return v
        raise ValueError(f"No dict found in {path}")
    else:
        # Try JSON as default
        return json.loads(p.read_text(encoding="utf-8"))


def _result_to_json(result: DiffResult) -> dict[str, Any]:
    """Convert a DiffResult to a JSON-serializable dict."""
    output: dict[str, Any] = {}

    if result.added:
        output["added"] = result.added
    if result.removed:
        output["removed"] = result.removed
    if result.changed:
        output["changed"] = {k: {"old": v.old, "new": v.new} for k, v in result.changed.items()}
    if result.type_changed:
        output["type_changed"] = {
            k: {"old_type": type(v.old).__name__, "old": v.old, "new_type": type(v.new).__name__, "new": v.new}
            for k, v in result.type_changed.items()
        }
    if result.children:
        output["children"] = {k: _result_to_json(v) for k, v in result.children.items()}

    return output
