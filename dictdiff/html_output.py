"""HTML output — generate beautiful, self-contained HTML diff reports.

Produces a single HTML file with embedded CSS that can be viewed in any
browser, shared via email, or archived for audit trails.
"""

from __future__ import annotations

import html
from datetime import datetime, timezone
from typing import Any

from dictdiff.core import DiffResult


def format_html(
    result: DiffResult,
    *,
    title: str = "dictdiff Report",
    old_label: str = "Old",
    new_label: str = "New",
    include_summary: bool = True,
    include_timestamp: bool = True,
    theme: str = "auto",
) -> str:
    """Generate a complete HTML page showing the diff.

    Args:
        result: The DiffResult to display.
        title: Page title and heading.
        old_label: Label for the old side.
        new_label: Label for the new side.
        include_summary: Whether to include the summary section.
        include_timestamp: Whether to include generation timestamp.
        theme: Color theme — "light", "dark", or "auto" (follows system).

    Returns:
        Complete HTML string.
    """
    summary = result.summary()
    timestamp = (
        datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        if include_timestamp
        else ""
    )

    rows_html = _build_rows(result, prefix="")
    summary_html = _build_summary(summary) if include_summary else ""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)}</title>
<style>
{CSS_LIGHT}
@media (prefers-color-scheme: dark) {{
{CSS_DARK}
}}
[data-theme="dark"] {{
{CSS_DARK}
}}
[data-theme="light"] {{
{CSS_LIGHT}
}}
</style>
</head>
<body>
<div class="container">
<h1>{html.escape(title)}</h1>
{f'<p class="timestamp">Generated: {html.escape(timestamp)}</p>' if timestamp else ""}
{summary_html}
<table>
<thead>
<tr>
<th>Path</th>
<th>Change</th>
<th>{html.escape(old_label)}</th>
<th>{html.escape(new_label)}</th>
</tr>
</thead>
<tbody>
{rows_html}
</tbody>
</table>
{f'<p class="footer">{_build_legend()}</p>' if not result.is_empty else '<p class="no-diff">No differences found.</p>'}
</div>
</body>
</html>"""


def format_html_standalone(
    result: DiffResult,
    *,
    title: str = "dictdiff Report",
    old_label: str = "Old",
    new_label: str = "New",
) -> str:
    """Generate a minimal standalone HTML diff without dark mode support.

    Useful for embedding in emails or contexts where CSS media queries
    are not supported.

    Args:
        result: The DiffResult to display.
        title: Page title and heading.
        old_label: Label for the old side.
        new_label: Label for the new side.

    Returns:
        Complete HTML string.
    """
    summary = result.summary()
    rows_html = _build_rows(result, prefix="")
    summary_html = _build_summary(summary)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>{html.escape(title)}</title>
<style>
{CSS_LIGHT}
</style>
</head>
<body>
<div class="container">
<h1>{html.escape(title)}</h1>
{summary_html}
<table>
<thead>
<tr><th>Path</th><th>Change</th><th>{html.escape(old_label)}</th><th>{html.escape(new_label)}</th></tr>
</thead>
<tbody>
{rows_html}
</tbody>
</table>
{_build_legend() if not result.is_empty else '<p class="no-diff">No differences found.</p>'}
</div>
</body>
</html>"""


def _build_rows(result: DiffResult, *, prefix: str) -> str:
    """Build HTML table rows from a DiffResult."""
    rows: list[str] = []

    # Added
    for key, value in result.added.items():
        path = f"{prefix}{key}"
        rows.append(
            f'<tr class="added">'
            f"<td>{html.escape(path)}</td>"
            f'<td><span class="badge added">added</span></td>'
            f'<td class="empty">—</td>'
            f"<td>{html.escape(_fmt(value))}</td>"
            f"</tr>"
        )

    # Removed
    for key, value in result.removed.items():
        path = f"{prefix}{key}"
        rows.append(
            f'<tr class="removed">'
            f"<td>{html.escape(path)}</td>"
            f'<td><span class="badge removed">removed</span></td>'
            f'<td class="strike">{html.escape(_fmt(value))}</td>'
            f'<td class="empty">—</td>'
            f"</tr>"
        )

    # Changed
    for key, change in result.changed.items():
        path = f"{prefix}{key}"
        rows.append(
            f'<tr class="changed">'
            f"<td>{html.escape(path)}</td>"
            f'<td><span class="badge changed">changed</span></td>'
            f'<td class="strike">{html.escape(_fmt(change.old))}</td>'
            f"<td>{html.escape(_fmt(change.new))}</td>"
            f"</tr>"
        )

    # Type changed
    for key, change in result.type_changed.items():
        path = f"{prefix}{key}"
        old_type = type(change.old).__name__
        new_type = type(change.new).__name__
        rows.append(
            f'<tr class="type-changed">'
            f"<td>{html.escape(path)}</td>"
            f'<td><span class="badge type-changed">{html.escape(old_type)}→{html.escape(new_type)}</span></td>'
            f'<td class="strike">{html.escape(_fmt(change.old))}</td>'
            f"<td>{html.escape(_fmt(change.new))}</td>"
            f"</tr>"
        )

    # Children
    for key, child in result.children.items():
        child_prefix = f"{prefix}{key}."
        rows.append(_build_rows(child, prefix=child_prefix))

    return "\n".join(rows)


def _build_summary(summary: dict[str, int]) -> str:
    """Build the summary section HTML."""
    parts: list[str] = []
    if summary["added"]:
        parts.append(f'<span class="stat added">+{summary["added"]} added</span>')
    if summary["removed"]:
        parts.append(f'<span class="stat removed">-{summary["removed"]} removed</span>')
    if summary["changed"]:
        parts.append(f'<span class="stat changed">~{summary["changed"]} changed</span>')
    if summary["type_changed"]:
        parts.append(
            f'<span class="stat type-changed">⇄{summary["type_changed"]} type changed</span>'
        )

    if not parts:
        return '<div class="summary">No differences found.</div>'

    return f'<div class="summary">{"".join(parts)}</div>'


def _build_legend() -> str:
    """Build a legend explaining the color codes."""
    return (
        '<span class="legend">'
        '<span class="badge added">added</span> '
        '<span class="badge removed">removed</span> '
        '<span class="badge changed">changed</span> '
        '<span class="badge type-changed">type changed</span>'
        "</span>"
    )


def _fmt(value: Any) -> str:
    """Format a value for display in HTML."""
    if isinstance(value, str):
        return f'"{value}"'
    if isinstance(value, bool):
        return str(value)
    if value is None:
        return "null"
    return repr(value)


# CSS for light theme
CSS_LIGHT = """
:root {
    --bg: #ffffff;
    --text: #1a1a2e;
    --border: #e0e0e0;
    --header-bg: #f5f5f5;
    --added-bg: #e8f5e9;
    --added-text: #2e7d32;
    --removed-bg: #ffebee;
    --removed-text: #c62828;
    --changed-bg: #fff8e1;
    --changed-text: #f57f17;
    --type-bg: #f3e5f5;
    --type-text: #7b1fa2;
}
body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    background: var(--bg);
    color: var(--text);
    margin: 0;
    padding: 20px;
    line-height: 1.6;
}
.container {
    max-width: 960px;
    margin: 0 auto;
}
h1 {
    border-bottom: 2px solid var(--border);
    padding-bottom: 10px;
}
.timestamp {
    color: #888;
    font-size: 0.85em;
}
.summary {
    margin: 15px 0;
    font-size: 1.1em;
}
.stat {
    margin-right: 15px;
}
.stat.added { color: var(--added-text); }
.stat.removed { color: var(--removed-text); }
.stat.changed { color: var(--changed-text); }
.stat.type-changed { color: var(--type-text); }
table {
    width: 100%;
    border-collapse: collapse;
    margin: 20px 0;
}
th {
    background: var(--header-bg);
    text-align: left;
    padding: 10px 12px;
    border: 1px solid var(--border);
    font-weight: 600;
}
td {
    padding: 8px 12px;
    border: 1px solid var(--border);
    vertical-align: top;
}
tr.added td { background: var(--added-bg); }
tr.removed td { background: var(--removed-bg); }
tr.changed td { background: var(--changed-bg); }
tr.type-changed td { background: var(--type-bg); }
td.empty { color: #ccc; }
td.strike { text-decoration: line-through; opacity: 0.7; }
.badge {
    display: inline-block;
    padding: 2px 8px;
    border-radius: 4px;
    font-size: 0.85em;
    font-weight: 500;
}
.badge.added { background: var(--added-bg); color: var(--added-text); }
.badge.removed { background: var(--removed-bg); color: var(--removed-text); }
.badge.changed { background: var(--changed-bg); color: var(--changed-text); }
.badge.type-changed { background: var(--type-bg); color: var(--type-text); }
.no-diff {
    color: var(--added-text);
    font-size: 1.2em;
    padding: 20px 0;
}
.footer {
    margin-top: 20px;
    color: #888;
    font-size: 0.85em;
}
.legend .badge {
    margin-right: 5px;
}
"""

# CSS overrides for dark theme
CSS_DARK = """
:root {
    --bg: #1a1a2e;
    --text: #e0e0e0;
    --border: #333355;
    --header-bg: #16213e;
    --added-bg: #1b3a1b;
    --added-text: #81c784;
    --removed-bg: #3a1b1b;
    --removed-text: #ef9a9a;
    --changed-bg: #3a3a1b;
    --changed-text: #ffd54f;
    --type-bg: #2d1b3a;
    --type-text: #ce93d8;
}
"""
