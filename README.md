# dictdiff

Semantic dict/JSON diff tool with rich terminal output.

## Features

- **Deep recursive diff** — compares nested dicts, lists, and scalars
- **Type-change detection** — flags when a key's value type changes (e.g. `"42"` → `42`)
- **Set-aware list diff** — optional set-mode for unordered list comparison
- **Rich terminal output** — color-coded, side-by-side or unified view
- **Multiple formats** — JSON, YAML, Python dict files as input
- **Exit codes** — 0 if identical, 1 if differences, 2 on error
- **Library API** — use `dictdiff.diff()` in your own Python code
- **Patch generation** — output a JSON patch (RFC 6902) describing changes

## Installation

```bash
pip install dictdiff
```

## CLI Usage

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

## Python API

```python
from dictdiff import diff

result = diff(
    {"a": 1, "b": [1, 2, 3]},
    {"a": 1, "b": [1, 2, 4], "c": "new"},
)
# result.added    → {"c": "new"}
# result.removed  → {}
# result.changed  → {"b": Change(old=[1,2,3], new=[1,2,4])}
# result.type_changed → {}
```

## License

MIT
