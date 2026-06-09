"""Rich terminal formatting for diff results."""

from __future__ import annotations

from typing import Any

from rich.console import Console
from rich.table import Table
from rich.text import Text
from rich.tree import Tree

from dictdiff.core import DiffResult


def format_diff(
    result: DiffResult, *, title: str = "Diff", show_types: bool = True
) -> None:
    """Print a rich, color-coded diff to the terminal.

    Args:
        result: The DiffResult to display.
        title: Title for the output.
        show_types: Whether to show type information for type changes.
    """
    console = Console()

    if result.is_empty:
        console.print("[green]✓ No differences found[/green]")
        return

    # Summary line
    summary = result.summary()
    parts = []
    if summary["added"]:
        parts.append(f"[green]+{summary['added']} added[/green]")
    if summary["removed"]:
        parts.append(f"[red]-{summary['removed']} removed[/red]")
    if summary["changed"]:
        parts.append(f"[yellow]~{summary['changed']} changed[/yellow]")
    if summary["type_changed"]:
        parts.append(f"[magenta]⇄{summary['type_changed']} type changed[/magenta]")

    console.print()
    console.print(f"[bold]{title}[/bold]  {'  '.join(parts)}")
    console.print()

    # Tree view
    tree = Tree("📋 Changes")
    _build_tree(tree, result, show_types=show_types)
    console.print(tree)


def _build_tree(
    tree: Tree, result: DiffResult, *, prefix: str = "", show_types: bool = True
) -> None:
    """Recursively build a rich Tree from a DiffResult."""
    # Added
    for key, value in result.added.items():
        label = Text()
        label.append(f"+ {prefix}{key}", style="green")
        label.append(f" = {_format_value(value)}", style="green")
        tree.add(label)

    # Removed
    for key, value in result.removed.items():
        label = Text()
        label.append(f"- {prefix}{key}", style="red")
        label.append(f" = {_format_value(value)}", style="red strike")
        tree.add(label)

    # Changed
    for key, change in result.changed.items():
        label = Text()
        label.append(f"~ {prefix}{key}", style="yellow")
        label.append(f": {_format_value(change.old)}", style="red strike")
        label.append(" → ", style="yellow")
        label.append(f"{_format_value(change.new)}", style="green")
        tree.add(label)

    # Type changed
    for key, change in result.type_changed.items():
        label = Text()
        label.append(f"⇄ {prefix}{key}", style="magenta")
        if show_types:
            label.append(
                f" ({type(change.old).__name__}→{type(change.new).__name__})",
                style="magenta dim",
            )
        label.append(f": {_format_value(change.old)}", style="red strike")
        label.append(" → ", style="magenta")
        label.append(f"{_format_value(change.new)}", style="green")
        tree.add(label)

    # Children
    for key, child in result.children.items():
        child_prefix = f"{prefix}{key}."
        if not child.is_empty:
            branch = tree.add(f"[bold]{prefix}{key}[/bold]")
            _build_tree(branch, child, prefix=child_prefix, show_types=show_types)


def format_unified(
    result: DiffResult, *, old_label: str = "old", new_label: str = "new"
) -> str:
    """Generate a unified-diff-style text output.

    Args:
        result: The DiffResult to format.
        old_label: Label for the old side.
        new_label: Label for the new side.

    Returns:
        Unified diff text.
    """
    lines: list[str] = []

    if result.is_empty:
        return ""

    _collect_unified(result, lines, prefix="")
    return "\n".join(lines)


def _collect_unified(result: DiffResult, lines: list[str], *, prefix: str) -> None:
    """Recursively collect unified diff lines."""
    for key, value in result.added.items():
        lines.append(f"+{prefix}{key}: {_format_value(value)}")

    for key, value in result.removed.items():
        lines.append(f"-{prefix}{key}: {_format_value(value)}")

    for key, change in result.changed.items():
        lines.append(f"-{prefix}{key}: {_format_value(change.old)}")
        lines.append(f"+{prefix}{key}: {_format_value(change.new)}")

    for key, change in result.type_changed.items():
        lines.append(
            f"-{prefix}{key}: ({type(change.old).__name__}) {_format_value(change.old)}"
        )
        lines.append(
            f"+{prefix}{key}: ({type(change.new).__name__}) {_format_value(change.new)}"
        )

    for key, child in result.children.items():
        _collect_unified(child, lines, prefix=f"{prefix}{key}.")


def format_table(result: DiffResult, *, title: str = "Diff") -> None:
    """Print a rich table with old/new values side by side.

    Args:
        result: The DiffResult to display.
        title: Title for the table.
    """
    console = Console()

    if result.is_empty:
        console.print("[green]✓ No differences found[/green]")
        return

    table = Table(title=title, show_lines=True)
    table.add_column("Path", style="bold")
    table.add_column("Change", justify="center")
    table.add_column("Old", style="red")
    table.add_column("New", style="green")

    _collect_table_rows(result, table, prefix="")

    console.print(table)


def _collect_table_rows(result: DiffResult, table: Table, *, prefix: str) -> None:
    """Recursively add rows to a rich Table."""
    for key, value in result.added.items():
        table.add_row(
            f"{prefix}{key}", "[green]added[/green]", "—", str(_format_value(value))
        )

    for key, value in result.removed.items():
        table.add_row(
            f"{prefix}{key}", "[red]removed[/red]", str(_format_value(value)), "—"
        )

    for key, change in result.changed.items():
        table.add_row(
            f"{prefix}{key}",
            "[yellow]changed[/yellow]",
            str(_format_value(change.old)),
            str(_format_value(change.new)),
        )

    for key, change in result.type_changed.items():
        table.add_row(
            f"{prefix}{key}",
            f"[magenta]{type(change.old).__name__}→{type(change.new).__name__}[/magenta]",
            str(_format_value(change.old)),
            str(_format_value(change.new)),
        )

    for key, child in result.children.items():
        _collect_table_rows(child, table, prefix=f"{prefix}{key}.")


def _format_value(value: Any) -> str:
    """Format a value for display."""
    if isinstance(value, str):
        return f'"{value}"'
    if isinstance(value, bool):
        return str(value)
    if value is None:
        return "null"
    return repr(value)
