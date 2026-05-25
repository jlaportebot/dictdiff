"""Rich-based formatting for dictdiff output."""

from __future__ import annotations

from typing import Any

from rich.console import Console
from rich.tree import Tree
from rich.text import Text
from rich.panel import Panel
from rich.table import Table

from .differ import ChangeKind, DiffEntry, count_changes, flatten


_KIND_STYLES: dict[ChangeKind, dict[str, str]] = {
    ChangeKind.ADDED: {"icon": "+", "color": "green", "label": "added"},
    ChangeKind.REMOVED: {"icon": "-", "color": "red", "label": "removed"},
    ChangeKind.TYPE_CHANGED: {"icon": "~", "color": "yellow", "label": "type_changed"},
    ChangeKind.VALUE_CHANGED: {"icon": "≠", "color": "cyan", "label": "changed"},
    ChangeKind.UNCHANGED: {"icon": " ", "color": "white", "label": "unchanged"},
}


def _format_value(val: Any, max_len: int = 60) -> str:
    s = repr(val)
    if len(s) > max_len:
        return s[: max_len - 3] + "..."
    return s


def _build_tree(entries: list[DiffEntry], tree: Tree) -> None:
    for entry in entries:
        style = _KIND_STYLES.get(entry.kind, _KIND_STYLES[ChangeKind.UNCHANGED])
        icon = style["icon"]
        color = style["color"]

        if entry.children:
            # Non-leaf node with changed children
            child_changes = count_changes(entry.children)
            summary = ", ".join(f"{v} {k}" for k, v in child_changes.items() if v > 0)
            label = Text()
            label.append(f"{icon} ", style="bold")
            label.append(entry.path, style=f"bold {color}")
            label.append(f"  ({summary})", style="dim")
            branch = tree.add(label)
            _build_tree(entry.children, branch)
        elif entry.kind == ChangeKind.ADDED:
            label = Text()
            label.append(f"{icon} ", style="bold green")
            label.append(entry.path, style="bold green")
            label.append(f"  = {_format_value(entry.new_value)}", style="green")
            tree.add(label)
        elif entry.kind == ChangeKind.REMOVED:
            label = Text()
            label.append(f"{icon} ", style="bold red")
            label.append(entry.path, style="bold red")
            label.append(f"  = {_format_value(entry.old_value)}", style="red")
            tree.add(label)
        elif entry.kind == ChangeKind.TYPE_CHANGED:
            label = Text()
            label.append(f"{icon} ", style="bold yellow")
            label.append(entry.path, style="bold yellow")
            label.append(f"  {entry.old_type}", style="red")
            label.append(" → ", style="dim")
            label.append(f"{entry.new_type}", style="green")
            tree.add(label)
        elif entry.kind == ChangeKind.VALUE_CHANGED:
            label = Text()
            label.append(f"{icon} ", style="bold cyan")
            label.append(entry.path, style="bold cyan")
            label.append(f"  {_format_value(entry.old_value)}", style="red")
            label.append(" → ", style="dim")
            label.append(f"{_format_value(entry.new_value)}", style="green")
            tree.add(label)


def render_tree(entries: list[DiffEntry], console: Console | None = None) -> None:
    """Render diff results as a rich tree."""
    console = console or Console()
    changes = count_changes(entries)

    if not any(v > 0 for v in changes.values()):
        console.print("[bold green]✓ No differences found.[/bold green]")
        return

    tree = Tree("dictdiff", guide_style="dim")
    _build_tree(entries, tree)
    console.print(tree)

    # Summary
    summary_parts = []
    for kind_name, count in changes.items():
        if count > 0:
            summary_parts.append(f"[bold]{count}[/bold] {kind_name}")
    console.print()
    console.print("  " + "  ".join(summary_parts))


def render_flat(entries: list[DiffEntry], console: Console | None = None) -> None:
    """Render diff results as a flat list (for scripting/piping)."""
    console = console or Console()
    flat = flatten(entries)

    if not flat:
        console.print("[bold green]✓ No differences found.[/bold green]")
        return

    for entry in flat:
        style = _KIND_STYLES.get(entry.kind, _KIND_STYLES[ChangeKind.UNCHANGED])
        icon = style["icon"]
        color = style["color"]

        if entry.kind == ChangeKind.ADDED:
            console.print(f"[{color}]{icon} {entry.path} = {_format_value(entry.new_value)}[/{color}]")
        elif entry.kind == ChangeKind.REMOVED:
            console.print(f"[{color}]{icon} {entry.path} = {_format_value(entry.old_value)}[/{color}]")
        elif entry.kind == ChangeKind.TYPE_CHANGED:
            console.print(
                f"[{color}]{icon} {entry.path}: {entry.old_type} -> {entry.new_type}[/{color}]"
            )
        elif entry.kind == ChangeKind.VALUE_CHANGED:
            console.print(
                f"[{color}]{icon} {entry.path}: {_format_value(entry.old_value)} -> {_format_value(entry.new_value)}[/{color}]"
            )


def render_json(entries: list[DiffEntry], console: Console | None = None) -> None:
    """Render diff results as JSON (for programmatic use)."""
    import json

    console = console or Console()
    flat = flatten(entries)
    output = []
    for entry in flat:
        item: dict[str, Any] = {
            "path": entry.path,
            "kind": entry.kind.value,
        }
        if entry.kind == ChangeKind.ADDED:
            item["new_value"] = entry.new_value
        elif entry.kind == ChangeKind.REMOVED:
            item["old_value"] = entry.old_value
        elif entry.kind == ChangeKind.TYPE_CHANGED:
            item["old_type"] = entry.old_type
            item["new_type"] = entry.new_type
            item["old_value"] = entry.old_value
            item["new_value"] = entry.new_value
        elif entry.kind == ChangeKind.VALUE_CHANGED:
            item["old_value"] = entry.old_value
            item["new_value"] = entry.new_value
        output.append(item)
    console.print(json.dumps(output, indent=2))
