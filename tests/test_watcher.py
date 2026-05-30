"""Tests for the watcher module."""

import json
import os
import tempfile
import time
import pytest
from pathlib import Path

from dictdiff.watcher import FileWatcher, MultiFileWatcher


class TestFileWatcher:
    """Tests for FileWatcher class."""

    def test_create_watcher(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f1:
            json.dump({"key": "initial"}, f1)
            f1.flush()
            old_path = f1.name
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f2:
            json.dump({"key": "new"}, f2)
            f2.flush()
            new_path = f2.name
        try:
            watcher = FileWatcher(old_path, new_path)
            assert watcher.old_path == Path(old_path)
            assert watcher.new_path == Path(new_path)
        finally:
            os.unlink(old_path)
            os.unlink(new_path)

    def test_check_initial(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f1:
            json.dump({"v": 1}, f1)
            f1.flush()
            old_path = f1.name
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f2:
            json.dump({"v": 2}, f2)
            f2.flush()
            new_path = f2.name
        try:
            watcher = FileWatcher(old_path, new_path)
            result = watcher.check()
            assert result is not None  # First check always returns a result
            assert watcher.change_count == 1
        finally:
            os.unlink(old_path)
            os.unlink(new_path)

    def test_check_no_change(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f1:
            json.dump({"v": 1}, f1)
            f1.flush()
            old_path = f1.name
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f2:
            json.dump({"v": 2}, f2)
            f2.flush()
            new_path = f2.name
        try:
            watcher = FileWatcher(old_path, new_path)
            watcher.check()  # Initial check
            result = watcher.check()  # No change → should return None
            assert result is None
        finally:
            os.unlink(old_path)
            os.unlink(new_path)

    def test_detect_file_change(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f1:
            json.dump({"v": 1}, f1)
            f1.flush()
            old_path = f1.name
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f2:
            json.dump({"v": 2}, f2)
            f2.flush()
            new_path = f2.name
        try:
            watcher = FileWatcher(old_path, new_path)
            watcher.check()  # Initial
            # Modify file
            time.sleep(0.1)
            with open(new_path, "w") as f:
                json.dump({"v": 3}, f)
            result = watcher.check()
            assert result is not None  # Should detect change
        finally:
            os.unlink(old_path)
            os.unlink(new_path)

    def test_nonexistent_file(self):
        watcher = FileWatcher("/nonexistent/old.json", "/nonexistent/new.json")
        # Should not crash on check
        result = watcher.check()
        # Should still return a result (empty)

    def test_stop(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f1:
            json.dump({"v": 1}, f1)
            f1.flush()
            old_path = f1.name
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f2:
            json.dump({"v": 2}, f2)
            f2.flush()
            new_path = f2.name
        try:
            watcher = FileWatcher(old_path, new_path)
            watcher.stop()  # Should not crash
        finally:
            os.unlink(old_path)
            os.unlink(new_path)


class TestMultiFileWatcher:
    """Tests for MultiFileWatcher class."""

    def test_create_multi_watcher(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f1:
            json.dump({"a": 1}, f1)
            f1.flush()
            old1 = f1.name
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f2:
            json.dump({"b": 2}, f2)
            f2.flush()
            new1 = f2.name
        try:
            watcher = MultiFileWatcher()
            watcher.add_pair(old1, new1)
            assert len(watcher.watchers) == 1
        finally:
            os.unlink(old1)
            os.unlink(new1)

    def test_total_changes(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f1:
            json.dump({"a": 1}, f1)
            f1.flush()
            old1 = f1.name
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f2:
            json.dump({"b": 2}, f2)
            f2.flush()
            new1 = f2.name
        try:
            watcher = MultiFileWatcher()
            watcher.add_pair(old1, new1)
            assert watcher.total_changes == 0
            # Trigger initial check
            for w in watcher.watchers:
                w.check()
            assert watcher.total_changes >= 1
        finally:
            os.unlink(old1)
            os.unlink(new1)

    def test_empty_watcher(self):
        watcher = MultiFileWatcher()
        assert watcher.total_changes == 0
