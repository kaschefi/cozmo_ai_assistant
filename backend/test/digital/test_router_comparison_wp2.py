# backend/test/digital/test_router_comparison_wp2.py
"""
Launcher bridge for WP2 LangSmith Router Benchmark.
Runs the WP2 evaluations across Laya and Ollama router architectures.
"""

import os
import sys

# Ensure backend directory is in path
backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

from test.digital.routers.test_wp2_langsmith_benchmark import run_wp2_benchmark

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Run WP2 Router Benchmark on LangSmith")
    parser.add_argument(
        "--experiment",
        "-e",
        type=str,
        default="laya",
        choices=["laya", "ollama", "all", "two_layer_laya", "single_layer_laya", "two_layer_ollama", "baseline_ollama"],
        help="Which experiments to run (default: 'laya')"
    )
    parser.add_argument(
        "--force-refresh",
        action="store_true",
        help="Re-sync and recreate dataset in LangSmith"
    )
    args = parser.parse_args()
    run_wp2_benchmark(experiment=args.experiment, force_refresh=args.force_refresh)
