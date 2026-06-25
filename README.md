# dictdiff

Semantic dict/JSON diff tool with rich terminal output.

[![PyPI](https://img.shields.io/pypi/v/dictdiff.svg)](https://pypi.org/project/dictdiff/)
[![Python](https://img.shields.io/pypi/pyversions/dictdiff.svg)](https://pypi.org/project/dictdiff/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Features

- **Deep recursive diff** — compares nested dicts, lists, and scalars
- **Type-change detection** — flags when a key's value type changes (e.g. `"42"` → `42`)
- **Set-aware list diff** — optional set-mode for unordered list comparison
- **LCS-based list diff** — smarter reordering detection with longest common subsequence
- **Rich terminal output** — color-coded tree, table, or unified diff views
- **HTML output** — generate beautiful, self-contained HTML reports with light/dark themes
- **Multiple formats** — JSON, YAML, TOML, INI, Python dict files as input
- **Exit codes** — 0 if identical, 1 if differences, 2 on error
- **Library API** — use `dictdiff.diff()` in your own Python code
- **Patch generation** — output a JSON patch (RFC 6902) describing changes
- **Patch application** — apply RFC 6902 patches to transform data
- **Three-way merge** — merge two modified versions against a common base (`dictdiff merge3`)
- **Ignore patterns** — glob, regex, prefix, exact, and dot-path ignore rules
- **Path extraction** — diff only a specific sub-path (e.g. `config.db`)
- **File watching** — monitor files for changes and show diffs in real-time (`dictdiff watch`)
- **Float tolerance** — configurable tolerance for floating-point comparison

## Installation

```bash
pip install dictdiff
```

Or with optional dependencies:

```bash
pip install dictdiff[yaml]     # YAML support
pip install dictdiff[toml]     # TOML support (Python < 3.11)
pip install dictdiff[html]     # HTML report generation
pip install dictdiff[watch]    # File watching support
pip install dictdiff[all]      # All optional features
```

## Quick Start

```bash
# Compare two JSON files
dictdiff file1.json file2.json

# Compare two YAML files
dictdiff config-old.yaml config-new.yaml

# Pipe JSON from stdin
dictdiff - < new.json

# Output as JSON patch (RFC 6902)
dictdiff --patch old.json new.json

# Set-mode for unordered list comparison
dictdiff --set-mode a.json b.json

# Quiet mode — exit code only
dictdiff -q a.json b.json
```

## CLI Usage

### Basic Comparison

```bash
# Compare two files (auto-detects JSON/YAML/TOML/INI/Python)
dictdiff old.json new.json

# Compare with stdin
cat old.json | dictdiff - new.json
```

### Output Formats

```bash
# Tree view (default, Rich-based)
dictdiff old.json new.json

# Table view
dictdiff --format table old.json new.json

# Unified diff (git-like)
dictdiff --format unified old.json new.json

# JSON output
dictdiff --format json old.json new.json

# HTML report (self-contained, light/dark themes)
dictdiff --format html old.json new.html -o report.html

# JSON patch (RFC 6902)
dictdiff --patch old.json new.json
```

### Advanced Options

```bash
# Compare lists as unordered sets
dictdiff --set-mode a.json b.json

# LCS-based list diff (smarter reordering detection)
dictiff --lcs a.json b.json

# Ignore specific keys
dictiff --ignore metadata --ignore timestamp old.json new.json

# Ignore patterns (glob, regex, prefix, exact, dot-path)
dictiff --ignore-pattern "*.timestamp" --ignore-pattern "re:^temp_" old.json new.json

# Float comparison tolerance
dictiff --float-tolerance 0.001 old.json new.json

# Extract and compare only a specific path
dictiff --path config.database old.json new.json

# Quiet mode (exit code only)
dictiff -q old.json new.json
```

### Patch Operations

```bash
# Generate RFC 6902 JSON Patch
dictiff --patch old.json new.json > patch.json

# Apply a patch
dictiff --apply patch.json old.json > new.json
```

### Three-Way Merge

```bash
# Merge two modified versions against a common base
dictiff --merge base.json ours.json theirs.json

# Resolve conflicts preferring 'theirs'
dictiff --merge base.json ours.json theirs.json --theirs-wins

# Output merge result as JSON
dictiff --merge base.json ours.json theirs.json --format json
```

### Path Extraction

```bash
# Compare only a specific sub-path
dictiff --path config.database old.json new.json
```

### HTML Reports

```bash
# Generate beautiful HTML report
dictiff --format html old.json new.json -o report.html

# The HTML includes:
# - Light/dark theme (auto-detects system preference)
# - Color-coded diff table
# - Summary statistics
# - Hover tooltips for values
# - Fully self-contained (no external CSS/JS)
```

### File Watching

```bash
# Watch files for changes and show diffs in real-time
dictiff watch old.json new.json

# Custom poll interval and output format
dictiff watch old.json new.json --interval 0.5 --format unified

# Watch multiple file pairs
dictiff watch --pairs old1.json new1.json --pairs old2.json new2.json
```

### Ignore Patterns

```bash
# Exact key match
dictiff --ignore-pattern "metadata" old.json new.json

# Glob patterns
dictiff --ignore-pattern "*.timestamp" --ignore-pattern "*.id" old.json new.json

# Regex patterns
dictiff --ignore-pattern "re:^temp_" old.json new.json

# Prefix matching
dictiff --ignore-pattern "/config.internal" old.json new.json

# Exact key (no special chars)
dictiff --ignore-pattern "secret" old.json new.json

# Dot-path (exact full path)
dictiff --ignore-pattern "/config.db.password" old.json new.json
```

## Python API

```python
from dictdiff import diff
from dictdiff.convenience import diff_files
from dictdiff.patch import generate_patch, apply_patch
from dictdiff.merge3 import merge3
from dictdiff.html_output import format_html

# Basic diff
result = diff(
    {"a": 1, "b": [1, 2, 3]},
    {"a": 1, "b": [1, 2, 4], "c": "new"},
)

# Result attributes
result.added      # {"c": "new"}
result.removed    # {}
result.changed    # {"b": Change(old=[1,2,3], new=[1,2,4])}
result.type_changed  # {}

# Convert to dict for serialization
result.to_dict()

# File-based diff (auto-loads JSON/YAML/TOML)
result = diff_files("old.json", "new.json")

# Generate RFC 6902 patch
patch = generate_patch(result)

# Apply patch
new_data = apply_patch(old_data, patch)

# Three-way merge
merged = merge3(base, ours, theirs)
if merged.has_conflicts:
    for conflict in merged.conflicts:
        print(f"Conflict at {conflict.key}")
```

## File Formats

| Extension | Format | Requirements |
|-----------|--------|--------------|
| `.json` | JSON | Built-in |
| `.yaml`, `.yml` | YAML | `pip install pyyaml` |
| `.toml` | TOML | Python 3.11+ or `pip install tomli` |
| `.ini`, `.cfg` | INI | Built-in |
| `.py` | Python dict | Built-in |

## Health Status

Each change is categorized:

| Category | Symbol | Description |
|----------|--------|-------------|
| Added | `+` | Key exists only in new |
| Removed | `-` | Key exists only in old |
| Changed | `~` | Value changed |
| Type Changed | `⇄` | Type changed (e.g. str → int) |

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Files are identical (or `--quiet` with no differences) |
| 1 | Differences found |
| 2 | Error during execution |

## Development

```bash
# Clone and setup
git clone https://github.com/jlaportebot/dictdiff.git
cd dictdiff
pip install -e ".[dev,all]"

# Run tests
pytest

# Lint
ruff check .

# Format
ruff format .
```

## License

MIT

---

**dictdiff** — Built with 🦞 by Mister Lobster