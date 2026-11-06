# backend/test/routers/line_chart.py
"""
Benchmark Line Chart Generator for Router Scalability Tracking.

Generates one line data chart per model across the full suite of experiments (20, 30, 50, 100 tools),
comparing how the model scales in:
1. Accuracy (%) vs Number of Tools
2. Latency P50 & Mean (ms) vs Number of Tools
3. LLM Token Usage vs Number of Tools

Also supports generating a combined multi-model comparison line chart.
Saves output charts to: `docs/charts/<phase>/models/`.
"""

import os
import sys
import argparse
from typing import Dict, Any, List, Optional
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# Ensure backend directory is in path
backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
project_root = os.path.abspath(os.path.join(backend_path, "../"))
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

from test.routers.saver import load_all_results_for_phase


def get_model_charts_dir(phase: str = "phase1") -> str:
    """Returns directory in `docs/charts/<phase>/models`."""
    charts_dir = os.path.join(project_root, "docs", "charts", phase, "models")
    os.makedirs(charts_dir, exist_ok=True)
    return charts_dir


def normalize_model_key(exp_name: str) -> str:
    """
    Normalizes experiment names across scales to group them by model architecture.
    Examples:
      '50-Tools-1-L-Laya-TopK' -> '1-L-Laya-TopK'
      '20-Tools-Baseline-LLM' -> 'Baseline-LLM'
    """
    for scale in ["20-Tools-", "30-Tools-", "50-Tools-", "100-Tools-", "20_Tools_", "30_Tools_", "50_Tools_", "100_Tools_"]:
        if scale in exp_name:
            return exp_name.replace(scale, "")
    return exp_name


def generate_line_chart_for_model(
    model_name: str,
    model_records: List[Dict[str, Any]],
    phase: str = "phase1"
) -> Optional[str]:
    """
    Generates a 3-panel line chart for a single model tracking its trajectory across scales:
    - Accuracy (%) vs Tools Scale
    - Latency (ms) vs Tools Scale
    - Token Usage vs Tools Scale
    """
    if not model_records:
        return None

    # Sort records by number of tools
    sorted_records = sorted(model_records, key=lambda r: int(r.get("num_tools", 0)))
    tool_scales = [int(r.get("num_tools", 0)) for r in sorted_records]
    accuracies = [float(r.get("accuracy", 0.0)) for r in sorted_records]
    p50_latencies = [float(r.get("p50_latency_ms", 0.0)) for r in sorted_records]
    mean_latencies = [float(r.get("mean_latency_ms", 0.0)) for r in sorted_records]
    tokens = [int(r.get("total_tokens", 0)) for r in sorted_records]

    fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(18, 5.2))
    fig.suptitle(f"Scalability Trajectory: {model_name} (Phase: {phase})", fontsize=14, fontweight="bold")

    # 1. Accuracy
    ax1.plot(tool_scales, accuracies, marker="o", color="#2563EB", linewidth=2.5, markersize=8, label="Accuracy (%)")
    for x, y in zip(tool_scales, accuracies):
        ax1.annotate(f"{y:.1f}%", (x, y), textcoords="offset points", xytext=(0, 10), ha="center", fontsize=9, fontweight="bold")
    ax1.set_title("Routing Accuracy (%) vs Tool Scale", fontsize=12, fontweight="bold")
    ax1.set_xlabel("Number of Tools", fontsize=10)
    ax1.set_ylabel("Accuracy (%)", fontsize=10)
    ax1.set_ylim(0, 105)
    ax1.set_xticks(tool_scales)
    ax1.grid(True, linestyle="--", alpha=0.5)

    # 2. Latency
    ax2.plot(tool_scales, p50_latencies, marker="s", color="#059669", linewidth=2.2, markersize=7, label="P50 (Median)")
    ax2.plot(tool_scales, mean_latencies, marker="^", color="#34D399", linewidth=1.8, linestyle="--", markersize=7, label="Mean")
    for x, y in zip(tool_scales, p50_latencies):
        ax2.annotate(f"{int(y)}ms", (x, y), textcoords="offset points", xytext=(0, 10), ha="center", fontsize=8.5)
    ax2.set_title("Routing Latency (ms) vs Tool Scale", fontsize=12, fontweight="bold")
    ax2.set_xlabel("Number of Tools", fontsize=10)
    ax2.set_ylabel("Latency (ms)", fontsize=10)
    ax2.set_xticks(tool_scales)
    ax2.legend(loc="upper left", fontsize=9)
    ax2.grid(True, linestyle="--", alpha=0.5)

    # 3. Token Usage
    ax3.plot(tool_scales, tokens, marker="D", color="#8B5CF6", linewidth=2.5, markersize=7, label="Tokens")
    for x, y in zip(tool_scales, tokens):
        lbl = f"{y:,}" if y > 0 else "0"
        ax3.annotate(lbl, (x, y), textcoords="offset points", xytext=(0, 10), ha="center", fontsize=8.5, fontweight="bold")
    ax3.set_title("Total Tokens vs Tool Scale", fontsize=12, fontweight="bold")
    ax3.set_xlabel("Number of Tools", fontsize=10)
    ax3.set_ylabel("Token Count", fontsize=10)
    ax3.set_xticks(tool_scales)
    ax3.grid(True, linestyle="--", alpha=0.5)

    plt.tight_layout()

    target_dir = get_model_charts_dir(phase)
    clean_model_name = model_name.replace(" ", "_").replace("/", "_")
    out_path = os.path.join(target_dir, f"line_chart_{clean_model_name}.png")
    plt.savefig(out_path, dpi=300, bbox_inches="tight")
    plt.close(fig)

    print(f"[LineChart] Saved line chart for model '{model_name}' to: {out_path}")
    return out_path


def generate_all_model_line_charts(phase: str = "phase1") -> List[str]:
    """
    Groups all stored results in the phase by model architecture and generates one line chart per model.
    """
    all_results = load_all_results_for_phase(phase)
    if not all_results:
        print(f"[LineChart] No results found in phase '{phase}'.")
        return []

    # Group by normalized model key
    models_data: Dict[str, List[Dict[str, Any]]] = {}
    for r in all_results:
        raw_name = r.get("model_id") or r.get("experiment_name", "Unknown")
        norm_key = normalize_model_key(raw_name)
        if norm_key not in models_data:
            models_data[norm_key] = []
        models_data[norm_key].append(r)

    generated = []
    for model_name, records in models_data.items():
        chart_path = generate_line_chart_for_model(model_name, records, phase=phase)
        if chart_path:
            generated.append(chart_path)

    return generated


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate scalability line charts per model across all experiments")
    parser.add_argument("--phase", "-p", type=str, default="phase1", help="Experiment phase (default: phase1)")
    args = parser.parse_args()

    generate_all_model_line_charts(phase=args.phase)

