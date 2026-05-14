"""
Unit tests for eval metrics. Run with: pytest tests/
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from eval.run_eval import tfidf_distance, argument_diversity, stance_drift, verdict_match


class TestTfidfDistance:
    def test_identical_strings_return_zero(self):
        a = "the quick brown fox jumps over the lazy dog"
        assert tfidf_distance(a, a) < 0.01

    def test_completely_different_returns_one(self):
        a = "artificial intelligence machine learning neural networks"
        b = "banana smoothie kitchen recipe blender"
        assert tfidf_distance(a, b) > 0.8

    def test_partial_overlap_returns_middle(self):
        a = "startup equity founder vesting risk"
        b = "startup equity founder vesting risk capital"
        d = tfidf_distance(a, b)
        assert 0.0 < d < 0.5

    def test_empty_strings_return_zero(self):
        assert tfidf_distance("", "") == 0.0
        assert tfidf_distance("hello world", "") == 0.0
        assert tfidf_distance("", "hello world") == 0.0


class TestArgumentDiversity:
    def test_identical_pro_con_low_diversity(self):
        text = "we should proceed because the upside is large"
        assert argument_diversity(text, text) < 0.01

    def test_opposing_pro_con_high_diversity(self):
        pro = "the upside is enormous and risks are manageable"
        con = "regulatory uncertainty makes this prohibitively dangerous"
        assert argument_diversity(pro, con) > 0.5


class TestStanceDrift:
    def test_no_drift_when_single_round(self):
        assert stance_drift(["only round"]) == 0.0

    def test_no_drift_when_empty(self):
        assert stance_drift([]) == 0.0

    def test_drift_when_rounds_differ(self):
        r1 = "the financial argument is the strongest reason here"
        r2 = "actually social factors dominate after considering opponent points"
        assert stance_drift([r1, r2]) > 0.3

    def test_no_drift_when_rounds_identical(self):
        r = "the financial argument is the strongest reason here"
        assert stance_drift([r, r]) < 0.01


class TestVerdictMatch:
    def test_exact_match(self):
        assert verdict_match("yes", "yes") is True
        assert verdict_match("no", "no") is True

    def test_case_insensitive(self):
        assert verdict_match("YES", "yes") is True
        assert verdict_match(" Yes ", "yes") is True

    def test_mismatch(self):
        assert verdict_match("yes", "no") is False
        assert verdict_match("no", "yes") is False

    def test_conditional_reference_accepts_any(self):
        # When reference is "conditional", any reasonable verdict counts.
        assert verdict_match("yes", "conditional") is True
        assert verdict_match("no", "conditional") is True
        assert verdict_match("conditional", "conditional") is True

    def test_empty_predicted_fails(self):
        assert verdict_match("", "yes") is False
        assert verdict_match(None, "yes") is False