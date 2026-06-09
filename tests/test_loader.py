"""Tests for the loader module."""

import json
import os
import tempfile
import pytest

from dictdiff.loader import load_file, load_string, detect_format, LoaderError


class TestDetectFormat:
    """Tests for detect_format function."""

    def test_json_extension(self):
        assert detect_format("data.json") == "json"

    def test_yaml_extension(self):
        assert detect_format("data.yaml") == "yaml"
        assert detect_format("data.yml") == "yaml"

    def test_toml_extension(self):
        assert detect_format("data.toml") == "toml"

    def test_ini_extension(self):
        assert detect_format("data.ini") == "ini"
        assert detect_format("data.cfg") == "ini"

    def test_python_extension(self):
        assert detect_format("config.py") == "python"

    def test_unknown_extension(self):
        assert detect_format("data.unknown") == "unknown"


class TestLoadString:
    """Tests for load_string function."""

    def test_json_string(self):
        data = load_string('{"name": "Alice", "age": 30}', format="json")
        assert data["name"] == "Alice"
        assert data["age"] == 30

    def test_json_array(self):
        data = load_string("[1, 2, 3]", format="json")
        assert data == [1, 2, 3]

    def test_json_invalid(self):
        with pytest.raises((LoaderError, json.JSONDecodeError)):
            load_string("{invalid json", format="json")

    def test_yaml_string(self):
        yaml_str = "name: Alice\nage: 30\n"
        try:
            data = load_string(yaml_str, format="yaml")
            assert data["name"] == "Alice"
        except (LoaderError, ImportError):
            pytest.skip("PyYAML not installed")

    def test_toml_string(self):
        toml_str = 'name = "Alice"\nage = 30\n'
        try:
            data = load_string(toml_str, format="toml")
            assert data["name"] == "Alice"
        except (LoaderError, ImportError):
            pytest.skip("tomli/tomllib not available")

    def test_unsupported_format(self):
        with pytest.raises((LoaderError, ValueError)):
            load_string("data", format="xml")


class TestLoadFile:
    """Tests for load_file function."""

    def test_load_json_file(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump({"key": "value"}, f)
            f.flush()
            path = f.name
        try:
            data = load_file(path)
            assert data["key"] == "value"
        finally:
            os.unlink(path)

    def test_load_yaml_file(self):
        try:
            import yaml  # noqa: F401
        except ImportError:
            pytest.skip("PyYAML not installed")
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("name: Alice\nage: 30\n")
            f.flush()
            path = f.name
        try:
            data = load_file(path)
            assert data["name"] == "Alice"
        finally:
            os.unlink(path)

    def test_load_toml_file(self):
        try:
            import tomllib  # noqa: F401
        except ImportError:
            try:
                import tomli  # noqa: F401
            except ImportError:
                pytest.skip("tomli/tomllib not available")
        with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
            f.write('name = "Alice"\nage = 30\n')
            f.flush()
            path = f.name
        try:
            data = load_file(path)
            assert data["name"] == "Alice"
        finally:
            os.unlink(path)

    def test_load_ini_file(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".ini", delete=False) as f:
            f.write("[database]\nhost = localhost\nport = 5432\n")
            f.flush()
            path = f.name
        try:
            data = load_file(path)
            assert "database" in data
        finally:
            os.unlink(path)

    def test_load_python_file(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write("CONFIG = {'debug': True, 'port': 8080}\n")
            f.flush()
            path = f.name
        try:
            data = load_file(path)
            # Python loader returns the dict value, not the namespace
            assert data == {"debug": True, "port": 8080}
        finally:
            os.unlink(path)

    def test_load_nonexistent_file(self):
        with pytest.raises(FileNotFoundError):
            load_file("/nonexistent/path/data.json")

    def test_auto_detect_format(self):
        """load_file should auto-detect format from extension."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump({"auto": True}, f)
            f.flush()
            path = f.name
        try:
            data = load_file(path)
            assert data["auto"] is True
        finally:
            os.unlink(path)


class TestLoaderError:
    """Tests for LoaderError exception."""

    def test_loader_error_is_exception(self):
        assert issubclass(LoaderError, Exception)

    def test_loader_error_has_path(self):
        err = LoaderError("/some/path.json", "bad format")
        assert err.path == "/some/path.json"
        assert "bad format" in err.message
