# backend/test/routers/line_chart.py
"""
Benchmark Line Chart Generator for Router Scalability Tracking.

Generates one line data chart per model across the full suite of experiments (20, 30, 50, 100 tools),
comparing how the model scales in:
1. Accuracy (%) vs Number of Tools
2. Latency P50 & Mean (ms) vs Number of Tools
3. LLM Tokens Per Call vs Number of Tools (Context Complexity)
4. Total Tokens Used vs Number of Tools (Cumulative Evaluation Cost)

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


def get_model_charts_dir(phase: str = "phase2") -> str:
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
      '2_L_LLM' -> '2-L-LLM'
    """
    for scale in ["20-Tools-", "30-Tools-", "50-Tools-", "100-Tools-", "20_Tools_", "30_Tools_", "50_Tools_", "100_Tools_"]:
        if scale in exp_name:
            exp_name = exp_name.replace(scale, "")
    # Normalize underscores to hyphens for canonical matching
    canonical_map = {
        "2_l_llm": "2-L-LLM",
        "2-l-llm": "2-L-LLM",
        "baseline_llm": "Baseline-LLM",
        "baseline-llm": "Baseline-LLM",
        "1_l_laya": "1-L-Laya",
        "1-l-laya": "1-L-Laya",
        "2_l_laya": "2-L-Laya",
        "2-l-laya": "2-L-Laya",
        "1_l_laya_topk": "1-L-Laya-TopK",
        "1-l-laya-topk": "1-L-Laya-TopK",
        "2_l_laya_topk": "2-L-Laya-TopK",
        "2-l-laya-topk": "2-L-Laya-TopK",
    }
    return canonical_map.get(exp_name.lower(), exp_name)


def generate_line_chart_for_model(
    model_name: str,
    model_records: List[Dict[str, Any]],
    phase: str = "phase2"
) -> Optional[str]:
    """
    Generates a 4-panel line chart for a single model tracking its trajectory across scales:
    1. Accuracy (%) vs Tools Scale
    2. Latency (ms) vs Tools Scale
    3. Tokens Per Call vs Tools Scale (Context Complexity)
    4. Cumulative Total Tokens vs Tools Scale
    """
    if not model_records:
        return None

    # Filter to standard benchmark scales (20, 30, 50, 100)
    valid_scales = {20, 30, 50, 100}
    filtered_records = [r for r in model_records if int(r.get("num_tools", 0)) in valid_scales]
    if not filtered_records:
        filtered_records = model_records

    # Sort records by number of tools
    sorted_records = sorted(filtered_records, key=lambda r: int(r.get("num_tools", 0)))
    tool_scales = [int(r.get("num_tools", 0)) for r in sorted_records]
    accuracies = [float(r.get("accuracy", 0.0)) for r in sorted_records]
    p50_latencies = [float(r.get("p50_latency_ms", 0.0)) for r in sorted_records]
    mean_latencies = [float(r.get("mean_latency_ms", 0.0)) for r in sorted_records]
    tokens_per_call = [float(r.get("avg_tokens_per_call", 0.0)) for r in sorted_records]
    total_tokens = [int(r.get("total_tokens", 0)) for r in sorted_records]

    is_laya = "laya" in model_name.lower()

    fig, (ax1, ax2, ax3, ax4) = plt.subplots(1, 4, figsize=(23, 5.2))
    fig.suptitle(f"Scalability Trajectory: {model_name} (Phase: {phase})", fontsize=14, fontweight="bold", y=0.98)

    # 1. Accuracy
    ax1.plot(tool_scales, accuracies, marker="o", color="#2563EB", linewidth=2.5, markersize=8, label="Accuracy (%)")
    for x, y in zip(tool_scales, accuracies):
        ax1.annotate(f"{y:.1f}%", (x, y), textcoords="offset points", xytext=(0, 10), ha="center", fontsize=9, fontweight="bold")
    ax1.set_title("Routing Accuracy (%)", fontsize=11, fontweight="bold")
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
    ax2.set_title("Routing Latency (ms)", fontsize=11, fontweight="bold")
    ax2.set_xlabel("Number of Tools", fontsize=10)
    ax2.set_ylabel("Latency (ms)", fontsize=10)
    ax2.set_xticks(tool_scales)
    ax2.legend(loc="upper left", fontsize=8.5)
    ax2.grid(True, linestyle="--", alpha=0.5)

    # 3. Tokens Per Call (Context Complexity)
    ax3.plot(tool_scales, tokens_per_call, marker="D", color="#0284C7", linewidth=2.5, markersize=7, label="Tokens / Call")
    for x, y in zip(tool_scales, tokens_per_call):
        lbl = f"{y:.0f}" if y > 0 else "0 (LAYA)"
        ax3.annotate(lbl, (x, y), textcoords="offset points", xytext=(0, 10), ha="center", fontsize=8.5, fontweight="bold")
    ax3.set_title("Avg Tokens Per LLM Call", fontsize=11, fontweight="bold")
    ax3.set_xlabel("Number of Tools", fontsize=10)
    ax3.set_ylabel("Tokens per Invocation", fontsize=10)
    max_tpc = max(tokens_per_call) if tokens_per_call else 10
    ax3.set_ylim(-10, max(max_tpc * 1.25, 20))
    ax3.set_xticks(tool_scales)
    ax3.grid(True, linestyle="--", alpha=0.5)

    # 4. Total Cumulative Tokens
    ax4.plot(tool_scales, total_tokens, marker="P", color="#8B5CF6", linewidth=2.5, markersize=7, label="Total Tokens")
    for x, y in zip(tool_scales, total_tokens):
        lbl = f"{y:,}" if y > 0 else "0 (LAYA)"
        ax4.annotate(lbl, (x, y), textcoords="offset points", xytext=(0, 10), ha="center", fontsize=8.5, fontweight="bold")
    ax4.set_title("Total Cumulative Tokens", fontsize=11, fontweight="bold")
    ax4.set_xlabel("Number of Tools", fontsize=10)
    ax4.set_ylabel("Total Tokens", fontsize=10)
    max_tot = max(total_tokens) if total_tokens else 10
    ax4.set_ylim(-10, max(max_tot * 1.2, 50))
    ax4.set_xticks(tool_scales)
    ax4.grid(True, linestyle="--", alpha=0.5)

    plt.tight_layout()

    target_dir = get_model_charts_dir(phase)
    clean_model_name = model_name.replace(" ", "_").replace("/", "_")
    out_path = os.path.join(target_dir, f"line_chart_{clean_model_name}.png")
    plt.savefig(out_path, dpi=300, bbox_inches="tight")
    plt.close(fig)

    print(f"[LineChart] Saved 4-panel line chart for model '{model_name}' to: {out_path}")
    return out_path


def generate_all_model_line_charts(phase: str = "phase2") -> List[str]:
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
    for model_name, records in sorted(models_data.items()):
        chart_path = generate_line_chart_for_model(model_name, records, phase=phase)
        if chart_path:
            generated.append(chart_path)

    return generated


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate scalability line charts per model across all experiments")
    parser.add_argument("--phase", "-p", type=str, default="phase2", help="Experiment phase (default: phase2)")
    args = parser.parse_args()

    generate_all_model_line_charts(phase=args.phase)
