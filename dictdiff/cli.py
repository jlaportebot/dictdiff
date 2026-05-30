"""CLI entry point for dictdiff."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import click

from dictdiff.core import DiffResult, diff
from dictdiff.formatter import format_diff, format_table, format_unified
from dictdiff.patch import generate_patch, apply_patch
from dictdiff.html_output import format_html
from dictdiff.loader import load_file, detect_format
from dictdiff.merge3 import merge3
from dictdiff.ignore import IgnoreMatcher, filter_dict
from dictdiff.paths import extract_path, list_paths


@click.command(context_settings={"help_option_names": ["-h", "--help"]})
@click.argument("old_file", type=click.Path(exists=False))
@click.argument("new_file", type=click.Path(exists=False))
@click.option("--set-mode", is_flag=True, default=False, help="Compare lists as unordered sets.")
@click.option("--lcs", "lcs_mode", is_flag=True, default=False, help="Use LCS-based list comparison (smarter reordering detection).")
@click.option("--patch", "output_patch", is_flag=True, default=False, help="Output RFC 6902 JSON Patch.")
@click.option("--apply", "apply_patch_file", type=click.Path(exists=False), default=None, help="Apply a JSON Patch file to OLD_FILE and output result.")
@click.option("--ignore", multiple=True, help="Keys to ignore during comparison (repeatable).")
@click.option("--ignore-pattern", multiple=True, help="Ignore patterns: glob, re:regex, /dotpath, or exact key.")
@click.option("--float-tolerance", type=float, default=0.0, help="Tolerance for float comparison.")
@click.option("--format", "fmt", type=click.Choice(["tree", "table", "unified", "json", "html"]), default="tree", help="Output format.")
@click.option("--html", "html_output", is_flag=True, default=False, help="Output as standalone HTML report (shorthand for --format html).")
@click.option("--quiet", "-q", is_flag=True, default=False, help="Only set exit code, no output.")
@click.option("--path", "dot_path", default=None, help="Compare only at a specific dot-path (e.g. 'config.db').")
@click.option("--merge", "merge_base", type=click.Path(exists=False), default=None, help="Three-way merge: BASE_FILE against OLD and NEW.")
@click.option("--ours-wins", is_flag=True, default=True, help="In merge conflicts, prefer 'ours' (left file).")
@click.option("--theirs-wins", is_flag=True, default=False, help="In merge conflicts, prefer 'theirs' (right file).")
@click.version_option(version="0.2.0")
def main(
    old_file: str,
    new_file: str,
    set_mode: bool,
    lcs_mode: bool,
    output_patch: bool,
    apply_patch_file: str | None,
    ignore: tuple[str, ...],
    ignore_pattern: tuple[str, ...],
    float_tolerance: float,
    fmt: str,
    html_output: bool,
    quiet: bool,
    dot_path: str | None,
    merge_base: str | None,
    ours_wins: bool,
    theirs_wins: bool,
) -> None:
    """Compare two JSON/YAML/TOML/INI/Python dict files semantically.

    OLD_FILE and NEW_FILE can be JSON (.json), YAML (.yaml/.yml),
    TOML (.toml), INI (.ini/.cfg), or Python dict (.py) files.
    Use '-' for stdin (JSON only).

    Use --merge for three-way merging: BASE_FILE is the common ancestor,
    OLD_FILE is 'ours', and NEW_FILE is 'theirs'.
    """
    try:
        old_data = _load_file(old_file)
        new_data = _load_file(new_file)
    except Exception as e:
        click.echo(f"Error loading files: {e}", err=True)
        sys.exit(2)

    # Apply ignore patterns
    if ignore_pattern:
        matcher = IgnoreMatcher.from_patterns(list(ignore_pattern))
        if isinstance(old_data, dict):
            old_data = filter_dict(old_data, matcher)
        if isinstance(new_data, dict):
            new_data = filter_dict(new_data, matcher)

    ignore_keys = set(ignore) if ignore else None

    # Three-way merge mode
    if merge_base is not None:
        try:
            base_data = _load_file(merge_base)
        except Exception as e:
            click.echo(f"Error loading base file: {e}", err=True)
            sys.exit(2)

        result = merge3(
            base_data,
            old_data,
            new_data,
            ours_wins=not theirs_wins,
            set_mode=set_mode,
            ignore_keys=ignore_keys,
            float_tolerance=float_tolerance,
        )

        if quiet:
            sys.exit(1 if result.has_conflicts else 0)

        if fmt == "json" or output_patch:
            click.echo(json.dumps(result.summary(), indent=2))
        else:
            _format_merge_result(result)
        sys.exit(1 if result.has_conflicts else 0)

    # Path-focused diff
    if dot_path is not None:
        try:
            old_data = extract_path(old_data, dot_path)
            new_data = extract_path(new_data, dot_path)
        except (KeyError, IndexError, ValueError) as e:
            click.echo(f"Error: path '{dot_path}' not found: {e}", err=True)
            sys.exit(2)

    # Apply patch mode
    if apply_patch_file is not None:
        try:
            patch_ops = _load_file(apply_patch_file)
            if not isinstance(patch_ops, list):
                raise ValueError("Patch file must contain a JSON array of operations")
            result = apply_patch(old_data, patch_ops)
            click.echo(json.dumps(result, indent=2))
            sys.exit(0)
        except Exception as e:
            click.echo(f"Error applying patch: {e}", err=True)
            sys.exit(2)

    result = diff(
        old_data, new_data,
        set_mode=set_mode,
        ignore_keys=ignore_keys,
        float_tolerance=float_tolerance,
        lcs_mode=lcs_mode,
    )

    if quiet:
        sys.exit(0 if result.is_empty else 1)

    if output_patch:
        patch_ops = generate_patch(result)
        click.echo(json.dumps(patch_ops, indent=2))
    elif html_output or fmt == "html":
        html_str = format_html(result, title=f"dictdiff: {old_file} vs {new_file}")
        click.echo(html_str)
    elif fmt == "tree":
        format_diff(result)
    elif fmt == "table":
        format_table(result)
    elif fmt == "unified":
        output = format_unified(result)
        if output:
            click.echo(output)
    elif fmt == "json":
        click.echo(json.dumps(result.to_dict(), indent=2))

    sys.exit(0 if result.is_empty else 1)


def _load_file(path: str) -> Any:
    """Load a data file using the unified loader."""
    if path == "-":
        return json.load(sys.stdin)
    return load_file(path)


def _format_merge_result(result: Any) -> None:
    """Format and display a three-way merge result."""
    from rich.console import Console
    from rich.table import Table

    console = Console()

    if result.has_conflicts:
        console.print(f"\n[bold red]⚠ {result.conflict_count} conflict(s) detected[/bold red]\n")

        if result.conflicts:
            table = Table(title="Merge Conflicts", show_lines=True)
            table.add_column("Path", style="bold")
            table.add_column("Base", style="dim")
            table.add_column("Ours", style="cyan")
            table.add_column("Theirs", style="magenta")

            for conflict in result.conflicts:
                table.add_row(
                    conflict.key,
                    repr(conflict.base_value),
                    repr(conflict.ours_value),
                    repr(conflict.theirs_value),
                )
            console.print(table)
    else:
        console.print("[green]✓ Merge completed with no conflicts[/green]")

    console.print(f"\n[bold]Merged result:[/bold]")
    console.print(json.dumps(result.merged, indent=2))


if __name__ == "__main__":
    main()
