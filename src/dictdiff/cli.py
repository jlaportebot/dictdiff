"""CLI entry point for dictdiff."""

from __future__ import annotations

import argparse
import sys

from rich.console import Console

from .differ import diff_dicts
from .loader import load_file
from .formatter import render_tree, render_flat, render_json


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="dictdiff",
        description="Smart structural diff for JSON, YAML, and TOML files.",
    )
    parser.add_argument("old", help="Path to the original file")
    parser.add_argument("new", help="Path to the new file")
    parser.add_argument(
        "-f",
        "--format",
        choices=["tree", "flat", "json"],
        default="tree",
        help="Output format (default: tree)",
    )
    parser.add_argument(
        "--no-color",
        action="store_true",
        help="Disable colored output",
    )
    parser.add_argument(
        "-q",
        "--quiet",
        action="store_true",
        help="Exit with code only (0=identical, 1=different)",
    )
    parser.add_argument(
        "-v",
        "--version",
        action="version",
        version=f"%(prog)s {_get_version()}",
    )
    return parser


def _get_version() -> str:
    from . import __version__

    return __version__


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    console = Console(no_color=args.no_color)

    try:
        old_data = load_file(args.old)
        new_data = load_file(args.new)
    except (FileNotFoundError, ValueError, ImportError) as exc:
        sys.stderr.write(f"Error: {exc}\n")
        return 2

    entries = diff_dicts(old_data, new_data)

    if args.quiet:
        return (
            0
            if not any(e.kind.value != "unchanged" and not e.children for e in entries)
            else 1
        )

    if args.format == "tree":
        render_tree(entries, console)
    elif args.format == "flat":
        render_flat(entries, console)
    elif args.format == "json":
        render_json(entries, console)

    # Exit code: 0 if identical, 1 if different
    from .differ import count_changes

    changes = count_changes(entries)
    return 1 if any(v > 0 for v in changes.values()) else 0


if __name__ == "__main__":
    sys.exit(main())
