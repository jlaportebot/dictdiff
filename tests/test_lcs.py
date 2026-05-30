"""Tests for the LCS (Longest Common Subsequence) module."""

import pytest
from dictdiff.lcs import compute_lcs, lcs_length, diff_lcs, EditOp, EditScript, diff_lcs_to_diff_result
from dictdiff.core import DiffResult


class TestLCSLength:
    """Tests for lcs_length function."""

    def test_empty_sequences(self):
        assert lcs_length([], []) == 0

    def test_identical_sequences(self):
        assert lcs_length([1, 2, 3], [1, 2, 3]) == 3

    def test_no_common(self):
        assert lcs_length([1, 2], [3, 4]) == 0

    def test_partial_overlap(self):
        assert lcs_length([1, 2, 3, 4], [2, 3, 5]) == 2

    def test_strings(self):
        assert lcs_length(list("ABCBDAB"), list("BDCAB")) == 4

    def test_single_element(self):
        assert lcs_length([1], [1]) == 1
        assert lcs_length([1], [2]) == 0


class TestComputeLCS:
    """Tests for compute_lcs function — returns index pairs."""

    def test_empty(self):
        assert compute_lcs([], []) == []

    def test_identical(self):
        result = compute_lcs([1, 2, 3], [1, 2, 3])
        assert len(result) == 3
        # All index pairs should match
        for i, (oi, ni) in enumerate(result):
            assert oi == i
            assert ni == i

    def test_no_common(self):
        result = compute_lcs([1, 2], [3, 4])
        assert result == []

    def test_partial(self):
        result = compute_lcs([1, 2, 3], [2, 3, 4])
        assert len(result) == 2  # [2, 3] are common
        # Old indices: 1, 2; New indices: 0, 1
        old_indices = [p[0] for p in result]
        new_indices = [p[1] for p in result]
        assert old_indices == [1, 2]
        assert new_indices == [0, 1]

    def test_index_pairs_within_bounds(self):
        old = [1, 2, 3, 4, 5]
        new = [2, 3, 5, 6]
        result = compute_lcs(old, new)
        for oi, ni in result:
            assert 0 <= oi < len(old)
            assert 0 <= ni < len(new)


class TestDiffLCS:
    """Tests for diff_lcs function (edit script generation)."""

    def test_identical(self):
        script = diff_lcs([1, 2, 3], [1, 2, 3])
        assert isinstance(script, EditScript)
        # Identical lists produce "equal" ops, not no ops
        assert all(op.op == "equal" for op in script.ops)
        non_equal = [op for op in script.ops if op.op != "equal"]
        assert len(non_equal) == 0

    def test_all_insertions(self):
        script = diff_lcs([], [1, 2, 3])
        insert_ops = [op for op in script.ops if op.op == "insert"]
        assert len(insert_ops) == 3

    def test_all_deletions(self):
        script = diff_lcs([1, 2, 3], [])
        delete_ops = [op for op in script.ops if op.op == "delete"]
        assert len(delete_ops) == 3

    def test_mixed_operations(self):
        script = diff_lcs([1, 2, 3], [2, 3, 4])
        non_equal_ops = [op for op in script.ops if op.op != "equal"]
        op_types = [op.op for op in non_equal_ops]
        assert any(t in op_types for t in ("insert", "delete", "replace"))

    def test_dict_lcs(self):
        old = [{"id": 1}, {"id": 2}, {"id": 3}]
        new = [{"id": 2}, {"id": 3}, {"id": 4}]
        script = diff_lcs(old, new)
        assert len(script.ops) > 0


class TestEditOp:
    """Tests for EditOp dataclass."""

    def test_create_insert_op(self):
        op = EditOp(op="insert", old_idx=None, new_idx=0, old_value=None, new_value=42)
        assert op.op == "insert"
        assert op.new_value == 42

    def test_create_delete_op(self):
        op = EditOp(op="delete", old_idx=2, new_idx=None, old_value=99, new_value=None)
        assert op.op == "delete"
        assert op.old_value == 99


class TestDiffLCSToDiffResult:
    """Tests for converting LCS diff to DiffResult."""

    def test_simple_list_diff(self):
        old = [1, 2, 3]
        new = [1, 3, 4]
        result = diff_lcs_to_diff_result(old, new)
        assert isinstance(result, DiffResult)
        assert not result.is_empty

    def test_identical_lists(self):
        old = [1, 2, 3]
        new = [1, 2, 3]
        result = diff_lcs_to_diff_result(old, new)
        assert result.is_empty
