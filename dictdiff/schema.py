"""Schema validation — define and enforce structure on dicts/JSON.

Provides a declarative schema language for validating that dicts conform
to expected types, required keys, value constraints, and nested structures.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any


class SchemaError(Exception):
    """Raised when a value does not conform to its schema."""

    def __init__(self, path: str, message: str) -> None:
        self.path = path
        self.message = message
        super().__init__(f"{path}: {message}")


@dataclass
class ValidationResult:
    """Result of schema validation."""

    errors: list[SchemaError] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        """True if no errors found."""
        return len(self.errors) == 0

    def add_error(self, path: str, message: str) -> None:
        self.errors.append(SchemaError(path, message))

    def add_warning(self, message: str) -> None:
        self.warnings.append(message)

    def merge(self, other: ValidationResult, *, prefix: str = "") -> None:
        """Merge another ValidationResult into this one."""
        for err in other.errors:
            self.errors.append(SchemaError(f"{prefix}{err.path}", err.message))
        self.warnings.extend(other.warnings)

    def summary(self) -> dict[str, Any]:
        """Return a summary dict."""
        return {
            "valid": self.is_valid,
            "error_count": len(self.errors),
            "warning_count": len(self.warnings),
            "errors": [{"path": e.path, "message": e.message} for e in self.errors],
        }


class SchemaType:
    """Base class for schema type definitions."""

    def validate(self, value: Any, path: str = "$") -> ValidationResult:
        raise NotImplementedError


@dataclass
class AnyType(SchemaType):
    """Accepts any value (no validation)."""

    nullable: bool = True

    def validate(self, value: Any, path: str = "$") -> ValidationResult:
        result = ValidationResult()
        if value is None and not self.nullable:
            result.add_error(path, "Value cannot be None")
        return result


@dataclass
class StringType(SchemaType):
    """Validates string values with optional pattern and length constraints."""

    min_length: int = 0
    max_length: int | None = None
    pattern: str | None = None
    nullable: bool = False

    def validate(self, value: Any, path: str = "$") -> ValidationResult:
        result = ValidationResult()
        if value is None:
            if not self.nullable:
                result.add_error(path, "Expected string, got None")
            return result
        if not isinstance(value, str):
            result.add_error(path, f"Expected string, got {type(value).__name__}")
            return result
        if len(value) < self.min_length:
            result.add_error(
                path, f"String length {len(value)} < minimum {self.min_length}"
            )
        if self.max_length is not None and len(value) > self.max_length:
            result.add_error(
                path, f"String length {len(value)} > maximum {self.max_length}"
            )
        if self.pattern is not None and not re.match(self.pattern, value):
            result.add_error(path, f"String does not match pattern '{self.pattern}'")
        return result


@dataclass
class IntType(SchemaType):
    """Validates integer values with optional range constraints."""

    minimum: int | None = None
    maximum: int | None = None
    nullable: bool = False

    def validate(self, value: Any, path: str = "$") -> ValidationResult:
        result = ValidationResult()
        if value is None:
            if not self.nullable:
                result.add_error(path, "Expected int, got None")
            return result
        if not isinstance(value, int) or isinstance(value, bool):
            result.add_error(path, f"Expected int, got {type(value).__name__}")
            return result
        if self.minimum is not None and value < self.minimum:
            result.add_error(path, f"Value {value} < minimum {self.minimum}")
        if self.maximum is not None and value > self.maximum:
            result.add_error(path, f"Value {value} > maximum {self.maximum}")
        return result


@dataclass
class FloatType(SchemaType):
    """Validates float values with optional range constraints."""

    minimum: float | None = None
    maximum: float | None = None
    nullable: bool = False

    def validate(self, value: Any, path: str = "$") -> ValidationResult:
        result = ValidationResult()
        if value is None:
            if not self.nullable:
                result.add_error(path, "Expected float, got None")
            return result
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            result.add_error(path, f"Expected float, got {type(value).__name__}")
            return result
        fval = float(value)
        if self.minimum is not None and fval < self.minimum:
            result.add_error(path, f"Value {fval} < minimum {self.minimum}")
        if self.maximum is not None and fval > self.maximum:
            result.add_error(path, f"Value {fval} > maximum {self.maximum}")
        return result


@dataclass
class BoolType(SchemaType):
    """Validates boolean values."""

    nullable: bool = False

    def validate(self, value: Any, path: str = "$") -> ValidationResult:
        result = ValidationResult()
        if value is None:
            if not self.nullable:
                result.add_error(path, "Expected bool, got None")
            return result
        if not isinstance(value, bool):
            result.add_error(path, f"Expected bool, got {type(value).__name__}")
        return result


@dataclass
class EnumType(SchemaType):
    """Validates that a value is one of a set of allowed values."""

    values: list[Any] = field(default_factory=list)
    nullable: bool = False

    def validate(self, value: Any, path: str = "$") -> ValidationResult:
        result = ValidationResult()
        if value is None:
            if not self.nullable:
                result.add_error(path, f"Expected one of {self.values}, got None")
            return result
        if value not in self.values:
            result.add_error(
                path, f"Value {value!r} not in allowed values {self.values!r}"
            )
        return result


@dataclass
class ListType(SchemaType):
    """Validates list values with optional element schema and length constraints."""

    element_type: SchemaType | None = None
    min_length: int = 0
    max_length: int | None = None
    nullable: bool = False

    def validate(self, value: Any, path: str = "$") -> ValidationResult:
        result = ValidationResult()
        if value is None:
            if not self.nullable:
                result.add_error(path, "Expected list, got None")
            return result
        if not isinstance(value, list):
            result.add_error(path, f"Expected list, got {type(value).__name__}")
            return result
        if len(value) < self.min_length:
            result.add_error(
                path, f"List length {len(value)} < minimum {self.min_length}"
            )
        if self.max_length is not None and len(value) > self.max_length:
            result.add_error(
                path, f"List length {len(value)} > maximum {self.max_length}"
            )
        if self.element_type is not None:
            for i, item in enumerate(value):
                child = self.element_type.validate(item, path=f"{path}[{i}]")
                result.merge(child)
        return result


@dataclass
class DictType(SchemaType):
    """Validates dict values with key schemas and constraints."""

    required_keys: dict[str, SchemaType] = field(default_factory=dict)
    optional_keys: dict[str, SchemaType] = field(default_factory=dict)
    allow_extra: bool = True
    nullable: bool = False

    def validate(self, value: Any, path: str = "$") -> ValidationResult:
        result = ValidationResult()
        if value is None:
            if not self.nullable:
                result.add_error(path, "Expected dict, got None")
            return result
        if not isinstance(value, dict):
            result.add_error(path, f"Expected dict, got {type(value).__name__}")
            return result

        # Check required keys
        for key, key_schema in self.required_keys.items():
            if key not in value:
                result.add_error(path, f"Missing required key '{key}'")
            else:
                child = key_schema.validate(value[key], path=f"{path}.{key}")
                result.merge(child)

        # Check optional keys
        for key, key_schema in self.optional_keys.items():
            if key in value:
                child = key_schema.validate(value[key], path=f"{path}.{key}")
                result.merge(child)

        # Check for extra keys
        if not self.allow_extra:
            known_keys = set(self.required_keys.keys()) | set(self.optional_keys.keys())
            extra_keys = set(value.keys()) - known_keys
            for key in sorted(extra_keys):
                result.add_error(path, f"Unexpected key '{key}'")

        return result


@dataclass
class UnionType(SchemaType):
    """Validates that a value matches at least one of multiple schemas."""

    types: list[SchemaType] = field(default_factory=list)
    nullable: bool = False

    def validate(self, value: Any, path: str = "$") -> ValidationResult:
        if value is None:
            result = ValidationResult()
            if not self.nullable:
                result.add_error(path, "Expected one of union types, got None")
            return result

        # Try each type; if any succeeds, return that
        best_result = None
        for schema_type in self.types:
            child = schema_type.validate(value, path=path)
            if child.is_valid:
                return child
            if best_result is None or len(child.errors) < len(best_result.errors):
                best_result = child

        # None matched — return the best (fewest errors) as the error report
        if best_result is not None:
            result = ValidationResult()
            result.add_error(
                path, f"Value does not match any of {len(self.types)} union types"
            )
            result.merge(best_result)
            return result

        result = ValidationResult()
        result.add_error(path, "Empty union type — no types defined")
        return result


def validate(value: Any, schema: SchemaType, *, path: str = "$") -> ValidationResult:
    """Validate a value against a schema.

    Args:
        value: The value to validate.
        schema: The schema to validate against.
        path: Root path for error messages.

    Returns:
        ValidationResult with any errors found.
    """
    return schema.validate(value, path=path)


def validate_diff_compatibility(
    old: Any,
    new: Any,
    schema: SchemaType,
) -> ValidationResult:
    """Validate that both old and new values conform to a schema before diffing.

    Useful to ensure that a diff is meaningful within a known structure.

    Args:
        old: The original value.
        new: The new value.
        schema: The schema both values should conform to.

    Returns:
        ValidationResult combining errors from both validations.
    """
    result = ValidationResult()
    old_result = validate(old, schema)
    new_result = validate(new, schema)
    result.merge(old_result, prefix="old/")
    result.merge(new_result, prefix="new/")
    if old_result.errors:
        result.add_warning(f"Old value has {len(old_result.errors)} schema violations")
    if new_result.errors:
        result.add_warning(f"New value has {len(new_result.errors)} schema violations")
    return result
