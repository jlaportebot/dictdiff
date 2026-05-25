# dictdiff

Smart structural diff for JSON, YAML, and TOML files — see exactly what changed, key by key.

## Why?

Standard diff tools work line-by-line. But when comparing config files, API responses, or data schemas, you want to know **which keys changed**, not which lines moved. `dictdiff` understands structure:

- ✅ Detects **added**, **removed**, **type-changed**, and **value-changed** keys
- ✅ Recursively diffs nested dicts
- ✅ Works with **JSON**, **YAML**, and **TOML** (and can mix them!)
- ✅ Beautiful tree output, flat mode, or JSON output for scripting
- ✅ Proper exit codes (0 = identical, 1 = different, 2 = error)

## Install

```bash
pip install dictdiff
```

For TOML support on Python < 3.11:

```bash
pip install dictdiff[toml]
```

## Usage

```bash
# Basic: compare two files (format auto-detected by extension)
dictdiff old.json new.json

# Compare YAML files
dictdiff config-v1.yaml config-v2.yaml

# Mix formats! JSON vs YAML
dictdiff baseline.json updated.yaml

# Flat output (one change per line, great for scripting)
dictdiff -f flat old.json new.json

# JSON output (for piping to jq, etc.)
dictdiff -f json old.json new.json

# Quiet mode — just exit code, no output
dictdiff -q old.json new.json
echo $?  # 0 if identical, 1 if different

# No color
dictdiff --no-color old.json new.json
```

## Example

```json
// old.json
{
  "database": {
    "host": "localhost",
    "port": 5432,
    "name": "myapp"
  },
  "debug": true
}
```

```json
// new.json
{
  "database": {
    "host": "db.example.com",
    "port": 5432,
    "name": "myapp_prod"
  },
  "debug": false,
  "logging": "verbose"
}
```

```
$ dictdiff old.json new.json
dictdiff
 ├─ 🔧 database  (1 value_changed)
 │   ├─ ≠ database.host  'localhost' → 'db.example.com'
 │   └─ ≠ database.name  'myapp' → 'myapp_prod'
 ├─ ≠ debug  True → False
 └─ + logging  = 'verbose'

  1 value_changed  1 added  1 changed
```

## Output Formats

| Format | Flag | Use When |
|--------|------|----------|
| Tree (default) | `-f tree` | Human review, understanding structure |
| Flat | `-f flat` | Quick scanning, grep-friendly |
| JSON | `-f json` | Programmatic use, piping to `jq` |

## As a Library

```python
from dictdiff import diff_dicts, load_file, flatten

old = load_file("config-v1.yaml")
new = load_file("config-v2.yaml")

entries = diff_dicts(old, new)
for change in flatten(entries):
    print(f"{change.kind.value}: {change.path}")
```

## License

MIT
