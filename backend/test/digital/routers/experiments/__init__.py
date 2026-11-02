# backend/test/digital/routers/experiments/__init__.py
"""
Router Benchmark Scaling Experiments Package.

Provides isolated experiment runners across tool counts:
- 20_tools:  63 test cases (MoKa_Router_Benchmark_20_Tools)
- 30_tools:  93 test cases (MoKa_Router_Benchmark_30_Tools)
- 50_tools: 153 test cases (MoKa_Router_Benchmark_50_Tools)
- 100_tools: 303 test cases (MoKa_Router_Benchmark_100_Tools)

Each experiment tests all 6 models from test/digital/routers/models:
- 2-L-Laya (Two-Layer LAYA)
- 1-L-Laya (Single-Layer LAYA)
- 2-L-Laya-TopK (Two-Layer LAYA Top-K)
- 1-L-Laya-TopK (Single-Layer LAYA Top-K)
- 2-L-LLM (Two-Layer LLM)
- Baseline-LLM (Monolithic Baseline LLM)
"""

import importlib

# Dynamic module access for numeric filename identifiers
tools_20 = importlib.import_module(".20_tools", package=__name__)
tools_30 = importlib.import_module(".30_tools", package=__name__)
tools_50 = importlib.import_module(".50_tools", package=__name__)
tools_100 = importlib.import_module(".100_tools", package=__name__)

run_20_tools_experiment = tools_20.run_20_tools_experiment
run_30_tools_experiment = tools_30.run_30_tools_experiment
run_50_tools_experiment = tools_50.run_50_tools_experiment
run_100_tools_experiment = tools_100.run_100_tools_experiment

__all__ = [
    "run_20_tools_experiment",
    "run_30_tools_experiment",
    "run_50_tools_experiment",
    "run_100_tools_experiment",
]

