# backend/test/digital/routers/benchmark_dataset/__init__.py
"""
Benchmark Datasets for Scaled Tool Routing Evaluation (N = 20, 30, 50, 100 tools).
Provides standardized test cases across the strict cumulative superset scaling tiers:
- tools_20:  63 test cases (20 tools + none)
- tools_30:  93 test cases (30 tools + none)
- tools_50: 153 test cases (50 tools + none)
- tools_100: 303 test cases (100 tools + none)
"""

from typing import Dict, List, Any
from .tools_20 import BENCHMARK_TEST_CASES as BENCHMARK_TEST_CASES_20
from .tools_30 import BENCHMARK_TEST_CASES as BENCHMARK_TEST_CASES_30
from .tools_50 import BENCHMARK_TEST_CASES as BENCHMARK_TEST_CASES_50
from .tools_100 import BENCHMARK_TEST_CASES as BENCHMARK_TEST_CASES_100

# Default backward-compatible benchmark cases alias
BENCHMARK_TEST_CASES = BENCHMARK_TEST_CASES_20

DATASET_PRESETS: Dict[int, List[Dict[str, str]]] = {
    20: BENCHMARK_TEST_CASES_20,
    30: BENCHMARK_TEST_CASES_30,
    50: BENCHMARK_TEST_CASES_50,
    100: BENCHMARK_TEST_CASES_100,
}


def get_benchmark_dataset(n: int = 20) -> List[Dict[str, str]]:
    """Returns the standardized benchmark evaluation dataset for N tools (20, 30, 50, 100)."""
    return DATASET_PRESETS.get(n, BENCHMARK_TEST_CASES_20)


__all__ = [
    "BENCHMARK_TEST_CASES",
    "BENCHMARK_TEST_CASES_20",
    "BENCHMARK_TEST_CASES_30",
    "BENCHMARK_TEST_CASES_50",
    "BENCHMARK_TEST_CASES_100",
    "DATASET_PRESETS",
    "get_benchmark_dataset",
]
