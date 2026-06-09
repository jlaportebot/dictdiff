"""Tests for the schema validation module."""

from dictdiff.schema import (
    ValidationResult,
    AnyType,
    StringType,
    IntType,
    FloatType,
    BoolType,
    EnumType,
    ListType,
    DictType,
    UnionType,
    validate,
    validate_diff_compatibility,
)


class TestValidationResult:
    """Tests for ValidationResult container."""

    def test_empty_result_is_valid(self):
        r = ValidationResult()
        assert r.is_valid is True
        assert len(r.errors) == 0

    def test_add_error_makes_invalid(self):
        r = ValidationResult()
        r.add_error("$", "bad value")
        assert r.is_valid is False
        assert len(r.errors) == 1

    def test_add_warning(self):
        r = ValidationResult()
        r.add_warning("something off")
        assert r.is_valid is True  # warnings don't invalidate
        assert len(r.warnings) == 1

    def test_merge(self):
        r1 = ValidationResult()
        r1.add_error("$.a", "err1")
        r2 = ValidationResult()
        r2.add_error("$.b", "err2")
        r2.add_warning("warn1")
        r1.merge(r2)
        assert len(r1.errors) == 2
        assert len(r1.warnings) == 1

    def test_merge_with_prefix(self):
        r1 = ValidationResult()
        r1.add_error("$.a", "err1")
        r2 = ValidationResult()
        r2.add_error("$.x", "err2")
        r1.merge(r2, prefix="child.")
        assert r1.errors[1].path == "child.$.x"

    def test_summary(self):
        r = ValidationResult()
        r.add_error("$.a", "err1")
        r.add_warning("warn1")
        s = r.summary()
        assert s["valid"] is False
        assert s["error_count"] == 1
        assert s["warning_count"] == 1
        assert len(s["errors"]) == 1


class TestAnyType:
    """Tests for AnyType schema."""

    def test_any_accepts_anything(self):
        s = AnyType()
        assert validate(42, s).is_valid
        assert validate("hello", s).is_valid
        assert validate([1, 2], s).is_valid
        assert validate(None, s).is_valid

    def test_any_non_nullable(self):
        s = AnyType(nullable=False)
        assert validate(42, s).is_valid
        assert validate(None, s).is_valid is False


class TestStringType:
    """Tests for StringType schema."""

    def test_valid_string(self):
        s = StringType()
        assert validate("hello", s).is_valid

    def test_invalid_type(self):
        s = StringType()
        result = validate(123, s)
        assert result.is_valid is False

    def test_min_length(self):
        s = StringType(min_length=3)
        assert validate("abc", s).is_valid
        assert validate("ab", s).is_valid is False

    def test_max_length(self):
        s = StringType(max_length=5)
        assert validate("abcde", s).is_valid
        assert validate("abcdef", s).is_valid is False

    def test_pattern(self):
        s = StringType(pattern=r"^\d{3}-\d{4}$")
        assert validate("123-4567", s).is_valid
        assert validate("abc-defg", s).is_valid is False

    def test_nullable(self):
        s = StringType(nullable=True)
        assert validate(None, s).is_valid
        s2 = StringType(nullable=False)
        assert validate(None, s2).is_valid is False

    def test_empty_string_passes_min_length_0(self):
        s = StringType(min_length=0)
        assert validate("", s).is_valid


class TestIntType:
    """Tests for IntType schema."""

    def test_valid_int(self):
        s = IntType()
        assert validate(42, s).is_valid

    def test_bool_not_int(self):
        s = IntType()
        assert validate(True, s).is_valid is False

    def test_float_not_int(self):
        s = IntType()
        assert validate(3.14, s).is_valid is False

    def test_minimum(self):
        s = IntType(minimum=0)
        assert validate(0, s).is_valid
        assert validate(-1, s).is_valid is False

    def test_maximum(self):
        s = IntType(maximum=100)
        assert validate(100, s).is_valid
        assert validate(101, s).is_valid is False

    def test_nullable(self):
        s = IntType(nullable=True)
        assert validate(None, s).is_valid


class TestFloatType:
    """Tests for FloatType schema."""

    def test_valid_float(self):
        s = FloatType()
        assert validate(3.14, s).is_valid

    def test_int_passes_float(self):
        s = FloatType()
        assert validate(42, s).is_valid

    def test_string_fails(self):
        s = FloatType()
        assert validate("3.14", s).is_valid is False

    def test_minimum(self):
        s = FloatType(minimum=0.0)
        assert validate(0.0, s).is_valid
        assert validate(-0.1, s).is_valid is False

    def test_maximum(self):
        s = FloatType(maximum=1.0)
        assert validate(1.0, s).is_valid
        assert validate(1.1, s).is_valid is False


class TestBoolType:
    """Tests for BoolType schema."""

    def test_valid_bool(self):
        s = BoolType()
        assert validate(True, s).is_valid
        assert validate(False, s).is_valid

    def test_int_not_bool(self):
        s = BoolType()
        assert validate(1, s).is_valid is False
        assert validate(0, s).is_valid is False


class TestEnumType:
    """Tests for EnumType schema."""

    def test_valid_enum(self):
        s = EnumType(values=["red", "green", "blue"])
        assert validate("red", s).is_valid
        assert validate("green", s).is_valid

    def test_invalid_enum(self):
        s = EnumType(values=["red", "green", "blue"])
        assert validate("yellow", s).is_valid is False

    def test_mixed_types(self):
        s = EnumType(values=[1, "two", True, None])
        assert validate(1, s).is_valid
        assert validate("two", s).is_valid
        assert validate(2, s).is_valid is False

    def test_empty_enum(self):
        s = EnumType(values=[])
        assert validate("anything", s).is_valid is False


class TestListType:
    """Tests for ListType schema."""

    def test_valid_list(self):
        s = ListType()
        assert validate([1, 2, 3], s).is_valid

    def test_non_list_fails(self):
        s = ListType()
        assert validate("not a list", s).is_valid is False

    def test_element_type(self):
        s = ListType(element_type=IntType())
        assert validate([1, 2, 3], s).is_valid
        result = validate([1, "two", 3], s)
        assert result.is_valid is False

    def test_min_length(self):
        s = ListType(min_length=2)
        assert validate([1, 2], s).is_valid
        assert validate([1], s).is_valid is False

    def test_max_length(self):
        s = ListType(max_length=2)
        assert validate([1, 2], s).is_valid
        assert validate([1, 2, 3], s).is_valid is False

    def test_nested_list(self):
        s = ListType(element_type=ListType(element_type=IntType()))
        assert validate([[1, 2], [3, 4]], s).is_valid
        assert validate([[1, "x"]], s).is_valid is False


class TestDictType:
    """Tests for DictType schema."""

    def test_valid_dict(self):
        s = DictType()
        assert validate({"key": "val"}, s).is_valid

    def test_non_dict_fails(self):
        s = DictType()
        assert validate([1, 2], s).is_valid is False

    def test_required_keys_present(self):
        s = DictType(
            required_keys={"name": StringType(), "age": IntType()},
        )
        assert validate({"name": "Alice", "age": 30}, s).is_valid

    def test_required_keys_missing(self):
        s = DictType(required_keys={"name": StringType()})
        assert validate({}, s).is_valid is False

    def test_optional_keys(self):
        s = DictType(
            required_keys={"name": StringType()},
            optional_keys={"age": IntType()},
        )
        assert validate({"name": "Alice"}, s).is_valid
        assert validate({"name": "Alice", "age": 30}, s).is_valid

    def test_optional_keys_wrong_type(self):
        s = DictType(
            required_keys={"name": StringType()},
            optional_keys={"age": IntType()},
        )
        result = validate({"name": "Alice", "age": "thirty"}, s)
        assert result.is_valid is False

    def test_allow_extra_true(self):
        s = DictType(allow_extra=True)
        assert validate({"key": "val", "extra": True}, s).is_valid

    def test_allow_extra_false(self):
        s = DictType(
            required_keys={"key": StringType()},
            allow_extra=False,
        )
        assert validate({"key": "val"}, s).is_valid
        result = validate({"key": "val", "extra": True}, s)
        assert len(result.errors) >= 1

    def test_nullable(self):
        s = DictType(
            required_keys={
                "user": DictType(
                    required_keys={"name": StringType()},
                ),
            },
        )
        assert validate({"user": {"name": "Alice"}}, s).is_valid
        assert validate({"user": {}}, s).is_valid is False


class TestUnionType:
    """Tests for UnionType schema."""

    def test_first_type_matches(self):
        s = UnionType(types=[StringType(), IntType()])
        assert validate("hello", s).is_valid

    def test_second_type_matches(self):
        s = UnionType(types=[StringType(), IntType()])
        assert validate(42, s).is_valid

    def test_no_type_matches(self):
        s = UnionType(types=[StringType(), IntType()])
        result = validate([1, 2, 3], s)
        assert result.is_valid is False

    def test_nullable(self):
        s = UnionType(types=[StringType()], nullable=True)
        assert validate(None, s).is_valid

    def test_empty_union(self):
        s = UnionType(types=[])
        result = validate("anything", s)
        assert result.is_valid is False


class TestValidateDiffCompatibility:
    """Tests for validate_diff_compatibility helper."""

    def test_both_valid(self):
        s = DictType(required_keys={"name": StringType()})
        result = validate_diff_compatibility({"name": "old"}, {"name": "new"}, s)
        assert result.is_valid

    def test_old_invalid(self):
        s = DictType(required_keys={"name": StringType()})
        result = validate_diff_compatibility({}, {"name": "new"}, s)
        assert result.is_valid is False
        assert len(result.warnings) >= 1

    def test_both_invalid(self):
        s = IntType()
        result = validate_diff_compatibility("not_int", "also_not", s)
        assert result.is_valid is False
        assert len(result.errors) >= 2


class TestSchemaComplex:
    """Tests for complex nested schemas."""

    def test_config_schema(self):
        """A realistic config validation."""
        db_schema = DictType(
            required_keys={
                "host": StringType(min_length=1),
                "port": IntType(minimum=1, maximum=65535),
                "name": StringType(min_length=1),
            },
            optional_keys={"ssl": BoolType()},
        )
        log_schema = DictType(
            optional_keys={
                "level": EnumType(values=["DEBUG", "INFO", "WARNING", "ERROR"]),
                "file": StringType(),
            },
        )
        config_schema = DictType(
            required_keys={"database": db_schema},
            optional_keys={"logging": log_schema},
        )

        # Valid config
        assert validate(
            {
                "database": {
                    "host": "localhost",
                    "port": 5432,
                    "name": "mydb",
                    "ssl": True,
                },
                "logging": {"level": "INFO", "file": "/var/log/app.log"},
            },
            config_schema,
        ).is_valid

        # Missing required database
        assert (
            validate({"logging": {"level": "DEBUG"}}, config_schema).is_valid is False
        )

        # Invalid port
        assert (
            validate(
                {"database": {"host": "localhost", "port": 99999, "name": "mydb"}},
                config_schema,
            ).is_valid
            is False
        )

        # Invalid enum value
        assert (
            validate(
                {
                    "database": {"host": "localhost", "port": 5432, "name": "mydb"},
                    "logging": {"level": "VERBOSE"},
                },
                config_schema,
            ).is_valid
            is False
        )

    def test_array_of_objects(self):
        item_schema = DictType(
            required_keys={"id": IntType(), "name": StringType()},
        )
        s = ListType(element_type=item_schema, min_length=1)
        assert validate(
            [{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}], s
        ).is_valid
        assert validate([], s).is_valid is False  # min_length=1
        assert validate([{"name": "NoId"}], s).is_valid is False

    def test_deeply_nested(self):
        inner = DictType(required_keys={"value": IntType()})
        middle = DictType(required_keys={"inner": inner})
        outer = DictType(required_keys={"middle": middle})
        assert validate({"middle": {"inner": {"value": 42}}}, outer).is_valid
        assert (
            validate({"middle": {"inner": {"value": "not_int"}}}, outer).is_valid
            is False
        )
