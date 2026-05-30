"""dictdiff — Semantic dict/JSON diff with rich terminal output."""

from dictdiff.core import Change, DiffResult, diff
from dictdiff.convenience import diff_files, diff_strings, diff_to_patch
from dictdiff.merge3 import merge3, MergeResult, MergeConflict
from dictdiff.schema import validate, SchemaType, ValidationResult, SchemaError
from dictdiff.lcs import diff_lcs, EditScript, EditOp
from dictdiff.ignore import IgnoreMatcher, IgnoreRule, filter_dict
from dictdiff.paths import extract_path, set_path, path_exists, list_paths, diff_paths

__all__ = [
    "diff",
    "diff_files",
    "diff_strings",
    "diff_to_patch",
    "DiffResult",
    "Change",
    "merge3",
    "MergeResult",
    "MergeConflict",
    "validate",
    "SchemaType",
    "ValidationResult",
    "SchemaError",
    "diff_lcs",
    "EditScript",
    "EditOp",
    "IgnoreMatcher",
    "IgnoreRule",
    "filter_dict",
    "extract_path",
    "set_path",
    "path_exists",
    "list_paths",
    "diff_paths",
]
__version__ = "0.2.0"
