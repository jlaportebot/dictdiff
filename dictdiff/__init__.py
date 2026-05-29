"""dictdiff — Semantic dict/JSON diff with rich terminal output."""

from dictdiff.core import Change, DiffResult, diff
from dictdiff.convenience import diff_files, diff_strings, diff_to_patch

__all__ = ["diff", "diff_files", "diff_strings", "diff_to_patch", "DiffResult", "Change"]
__version__ = "0.1.0"
