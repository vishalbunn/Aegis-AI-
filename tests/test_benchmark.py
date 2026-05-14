"""
Sanity-check the benchmark itself. The benchmark is the foundation —
if a query is malformed, the eval is meaningless.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from eval.benchmark import BENCHMARK


class TestBenchmark:
    def test_has_thirty_queries(self):
        assert len(BENCHMARK) == 30

    def test_each_query_has_required_fields(self):
        required = {"id", "query", "domain", "difficulty", "reference_lean", "key_factors"}
        for q in BENCHMARK:
            missing = required - set(q.keys())
            assert not missing, f"{q.get('id', '?')} missing fields: {missing}"

    def test_all_ids_unique(self):
        ids = [q["id"] for q in BENCHMARK]
        assert len(ids) == len(set(ids)), "duplicate IDs in benchmark"

    def test_valid_reference_leans(self):
        valid = {"yes", "no", "conditional"}
        for q in BENCHMARK:
            assert q["reference_lean"] in valid, f"{q['id']}: invalid reference_lean"

    def test_valid_difficulties(self):
        valid = {"simple", "moderate", "complex"}
        for q in BENCHMARK:
            assert q["difficulty"] in valid, f"{q['id']}: invalid difficulty"

    def test_valid_domains(self):
        valid = {"career", "business", "tech", "general", "healthcare"}
        for q in BENCHMARK:
            assert q["domain"] in valid, f"{q['id']}: invalid domain"

    def test_has_trap_cases(self):
        traps = [q for q in BENCHMARK if "trap" in q]
        assert len(traps) >= 5, "fewer than 5 trap cases"

    def test_trap_cases_have_trap_type(self):
        for q in BENCHMARK:
            if "trap" in q:
                assert q["trap"], f"{q['id']}: trap field empty"

    def test_queries_are_non_trivial(self):
        for q in BENCHMARK:
            assert len(q["query"]) > 30, f"{q['id']}: query too short"
            assert len(q["key_factors"]) >= 3, f"{q['id']}: too few key factors"