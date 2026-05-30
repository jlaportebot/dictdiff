"""Watch mode — monitor files for changes and show diffs in real-time.

Watches one or more file pairs and re-runs the diff whenever a file
is modified. Uses file-system polling for maximum portability.
"""

from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any

from dictdiff.core import DiffResult, diff
from dictdiff.formatter import format_unified
from dictdiff.patch import generate_patch


class FileWatcher:
    """Watches a pair of files and detects changes via content hashing."""

    def __init__(
        self,
        old_path: str | Path,
        new_path: str | Path,
        *,
        set_mode: bool = False,
        ignore_keys: set[str] | None = None,
        float_tolerance: float = 0.0,
        poll_interval: float = 1.0,
        output_format: str = "tree",
    ) -> None:
        self.old_path = Path(old_path)
        self.new_path = Path(new_path)
        self.set_mode = set_mode
        self.ignore_keys = ignore_keys or set()
        self.float_tolerance = float_tolerance
        self.poll_interval = poll_interval
        self.output_format = output_format

        self._old_hash: str | None = None
        self._new_hash: str | None = None
        self._last_result: DiffResult | None = None
        self._running = False
        self._change_count = 0

    @property
    def change_count(self) -> int:
        """Number of changes detected since start."""
        return self._change_count

    @property
    def last_result(self) -> DiffResult | None:
        """Last computed DiffResult."""
        return self._last_result

    def _hash_file(self, path: Path) -> str:
        """Compute SHA-256 hash of file contents."""
        if not path.exists():
            return ""
        content = path.read_bytes()
        return hashlib.sha256(content).hexdigest()

    def _load_file(self, path: Path) -> Any:
        """Load a JSON/YAML/TOML file."""
        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")

        suffix = path.suffix.lower()
        if suffix == ".json":
            return json.loads(path.read_text(encoding="utf-8"))
        elif suffix in (".yaml", ".yml"):
            try:
                import yaml
            except ImportError:
                raise ImportError("YAML support requires 'pyyaml' package")
            return yaml.safe_load(path.read_text(encoding="utf-8"))
        elif suffix == ".toml":
            try:
                import tomllib
            except ImportError:
                try:
                    import tomli as tomllib  # type: ignore[no-redef]
                except ImportError:
                    raise ImportError("TOML support requires Python 3.11+ or 'tomli' package")
            return tomllib.loads(path.read_text(encoding="utf-8"))
        else:
            return json.loads(path.read_text(encoding="utf-8"))

    def check(self) -> DiffResult | None:
        """Check if files changed and compute new diff if so.

        Returns:
            New DiffResult if files changed, None if unchanged.
        """
        old_hash = self._hash_file(self.old_path)
        new_hash = self._hash_file(self.new_path)

        if old_hash == self._old_hash and new_hash == self._new_hash:
            return None

        self._old_hash = old_hash
        self._new_hash = new_hash
        self._change_count += 1

        try:
            old_data = self._load_file(self.old_path)
            new_data = self._load_file(self.new_path)
        except Exception:
            # If loading fails, return empty result but don't crash
            return DiffResult()

        self._last_result = diff(
            old_data,
            new_data,
            set_mode=self.set_mode,
            ignore_keys=self.ignore_keys,
            float_tolerance=self.float_tolerance,
        )
        return self._last_result

    def run(self, *, max_iterations: int | None = None, callback: Any = None) -> None:
        """Run the watcher loop, checking files at the configured interval.

        Args:
            max_iterations: Maximum number of poll cycles (None = infinite).
            callback: Optional callable invoked with (DiffResult, change_count)
                      on each change. If None, prints to stdout.
        """
        self._running = True
        iterations = 0

        # Initial check
        result = self.check()
        if result is not None:
            self._report_change(result, callback)

        while self._running:
            time.sleep(self.poll_interval)
            iterations += 1

            if max_iterations is not None and iterations >= max_iterations:
                break

            result = self.check()
            if result is not None:
                self._report_change(result, callback)

    def stop(self) -> None:
        """Stop the watcher loop."""
        self._running = False

    def _report_change(self, result: DiffResult, callback: Any = None) -> None:
        """Report a detected change."""
        if callback is not None:
            callback(result, self._change_count)
            return

        # Default: print to stdout
        summary = result.summary()
        print(f"\n--- Change #{self._change_count} detected ---")
        print(f"  +{summary['added']} added  -{summary['removed']} removed  ~{summary['changed']} changed  ⇄{summary['type_changed']} type changed")

        if self.output_format == "unified":
            output = format_unified(result)
            if output:
                print(output)
        elif self.output_format == "patch":
            ops = generate_patch(result)
            print(json.dumps(ops, indent=2))
        elif self.output_format == "json":
            from dictdiff.cli import _result_to_json
            print(json.dumps(_result_to_json(result), indent=2))
        else:
            # tree format (rich)
            from dictdiff.formatter import format_diff
            format_diff(result, title=f"Change #{self._change_count}")


class MultiFileWatcher:
    """Watch multiple file pairs simultaneously."""

    def __init__(self, *, poll_interval: float = 1.0, output_format: str = "tree") -> None:
        self.poll_interval = poll_interval
        self.output_format = output_format
        self.watchers: list[FileWatcher] = []
        self._running = False

    def add_pair(
        self,
        old_path: str | Path,
        new_path: str | Path,
        *,
        set_mode: bool = False,
        ignore_keys: set[str] | None = None,
        float_tolerance: float = 0.0,
    ) -> None:
        """Add a file pair to watch."""
        watcher = FileWatcher(
            old_path,
            new_path,
            set_mode=set_mode,
            ignore_keys=ignore_keys,
            float_tolerance=float_tolerance,
            poll_interval=self.poll_interval,
            output_format=self.output_format,
        )
        self.watchers.append(watcher)

    def run(self, *, max_iterations: int | None = None) -> None:
        """Run all watchers in a single polling loop."""
        self._running = True
        iterations = 0

        # Initial check for all
        for w in self.watchers:
            result = w.check()
            if result is not None:
                w._report_change(result)

        while self._running:
            time.sleep(self.poll_interval)
            iterations += 1

            if max_iterations is not None and iterations >= max_iterations:
                break

            for w in self.watchers:
                result = w.check()
                if result is not None:
                    w._report_change(result)

    def stop(self) -> None:
        """Stop all watchers."""
        self._running = False
        for w in self.watchers:
            w.stop()

    @property
    def total_changes(self) -> int:
        """Total changes across all watchers."""
        return sum(w.change_count for w in self.watchers)
