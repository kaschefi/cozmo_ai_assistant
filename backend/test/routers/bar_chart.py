# backend/test/routers/bar_chart.py
"""
Benchmark Horizontal Bar Chart Generator for Individual Router Experiments.

Generates a publication-ready comparative horizontal bar chart for a single experiment scale (e.g. 20 or 50 tools),
comparing all evaluated models side-by-side on:
1. Accuracy (%)
2. Routing Latency P50 & Mean (ms)
3. Total Token Usage (0 for LAYA models)

Saves output charts to: `docs/charts/phase1/` (or specified phase directory).
"""

import os
import sys
import argparse
from typing import Dict, Any, List, Optional
import matplotlib
# Set backend before pyplot import to support headless execution
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

# Ensure backend directory is in path
backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
project_root = os.path.abspath(os.path.join(backend_path, "../"))
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

from test.routers.saver import load_results_for_tools, load_all_results_for_phase


def get_charts_dir(phase: str = "phase3") -> str:
    """Returns directory in `docs/charts/<phase>`."""
    charts_dir = os.path.join(project_root, "docs", "charts", phase)
    os.makedirs(charts_dir, exist_ok=True)
    return charts_dir


def generate_bar_chart_for_results(
    results: List[Dict[str, Any]],
    num_tools: int,
    phase: str = "phase3",
    output_filename: Optional[str] = None
) -> Optional[str]:
    """
    Renders a 3-panel horizontal bar chart comparing models in a single experiment scale.
    Panels (left to right):
      1. Accuracy (%)
      2. Routing Latency P50 & Mean (ms)
      3. Total LLM Tokens Used
    """
    if not results:
        print(f"[BarChart] No results provided for {num_tools} tools. Skipping chart generation.")
        return None

    # Predefined display order (top-to-bottom on horizontal chart)
    model_order = [
        "Baseline-LLM", "2-L-LLM", "1-L-Laya", "2-L-Laya", "1-L-Laya-TopK", "2-L-Laya-TopK"
    ]
    
    def sort_key(r):
        name = r.get("model_id") or r.get("experiment_name", "")
        for idx, mo in enumerate(model_order):
            if mo in name:
                return idx
        return 99

    sorted_results = sorted(results, key=sort_key)

    labels = []
    accuracies = []
    p50_latencies = []
    mean_latencies = []
    tokens = []

    for r in sorted_results:
        name = r.get("model_id") or r.get("experiment_name", "Unknown")
        short_name = name.replace(f"{num_tools}-Tools-", "").replace(f"{num_tools}_Tools_", "")
        labels.append(short_name)
        accuracies.append(float(r.get("accuracy", 0.0)))
        p50_latencies.append(float(r.get("p50_latency_ms", 0.0)))
        mean_latencies.append(float(r.get("mean_latency_ms", 0.0)))
        tokens.append(int(r.get("total_tokens", 0)))

    y = np.arange(len(labels))
    fig_height = max(4.0, len(labels) * 0.9 + 1.8)
    fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(18, fig_height))
    fig.suptitle(f"MoKa Router Benchmark ({num_tools} Tools) - Phase: {phase}", fontsize=14, fontweight="bold", y=0.98)

    colors = ["#2563EB", "#3B82F6", "#60A5FA", "#93C5FD", "#F59E0B", "#EF4444"]
    bar_colors = [colors[i % len(colors)] for i in range(len(labels))]

    # 1. Accuracy (Horizontal)
    bars1 = ax1.barh(y, accuracies, color=bar_colors, height=0.55, edgecolor="#1E293B", linewidth=0.8)
    ax1.set_title("Routing Accuracy (%)", fontsize=12, fontweight="bold", pad=12)
    ax1.set_xlabel("Accuracy (%)", fontsize=10)
    ax1.set_xlim(0, 115)
    ax1.set_yticks(y)
    ax1.set_yticklabels(labels, fontsize=10, fontweight="bold")
    ax1.grid(axis="x", linestyle="--", alpha=0.5)
    for bar in bars1:
        xval = bar.get_width()
        ax1.text(xval + 1.5, bar.get_y() + bar.get_height() / 2.0, f"{xval:.1f}%", va="center", ha="left", fontsize=9, fontweight="bold")

    # 2. Latency (Horizontal grouped: P50 & Mean)
    height = 0.32
    bars2_p50 = ax2.barh(y + height/2, p50_latencies, height, label="P50 (Median)", color="#059669", edgecolor="#064E3B", linewidth=0.8)
    bars2_mean = ax2.barh(y - height/2, mean_latencies, height, label="Mean", color="#34D399", edgecolor="#064E3B", linewidth=0.8)
    ax2.set_title("Latency (ms)", fontsize=12, fontweight="bold", pad=12)
    ax2.set_xlabel("Milliseconds (ms)", fontsize=10)
    max_lat = max(max(p50_latencies + mean_latencies, default=100.0), 10.0)
    ax2.set_xlim(0, max_lat * 1.25)
    ax2.set_yticks(y)
    ax2.set_yticklabels([])  # Hide redundant labels
    ax2.legend(loc="lower right", fontsize=8.5)
    ax2.grid(axis="x", linestyle="--", alpha=0.5)
    for bar in bars2_p50:
        xval = bar.get_width()
        ax2.text(xval + max_lat * 0.02, bar.get_y() + bar.get_height() / 2.0, f"{int(xval)}ms", va="center", ha="left", fontsize=8)
    for bar in bars2_mean:
        xval = bar.get_width()
        ax2.text(xval + max_lat * 0.02, bar.get_y() + bar.get_height() / 2.0, f"{int(xval)}ms", va="center", ha="left", fontsize=8)

    # 3. Token Usage (Horizontal)
    bars3 = ax3.barh(y, tokens, color="#8B5CF6", height=0.55, edgecolor="#4C1D95", linewidth=0.8)
    ax3.set_title("Total LLM Tokens Used", fontsize=12, fontweight="bold", pad=12)
    ax3.set_xlabel("Tokens Count", fontsize=10)
    max_tok = max(max(tokens, default=100), 10)
    ax3.set_xlim(0, max_tok * 1.25 if max_tok > 0 else 10)
    ax3.set_yticks(y)
    ax3.set_yticklabels([])  # Hide redundant labels
    ax3.grid(axis="x", linestyle="--", alpha=0.5)
    for idx, bar in enumerate(bars3):
        xval = bar.get_width()
        model_lbl = labels[idx].lower()
        if "laya" in model_lbl:
            display_txt = "0 (LAYA)"
        else:
            display_txt = f"{xval:,}"
        ax3.text(xval + (max_tok * 0.02 if max_tok > 0 else 0.5), bar.get_y() + bar.get_height() / 2.0, display_txt, va="center", ha="left", fontsize=8.5, fontweight="bold")

    plt.tight_layout()

    # Save chart
    target_dir = get_charts_dir(phase)
    fname = output_filename or f"bar_chart_{num_tools}_tools.png"
    out_path = os.path.join(target_dir, fname)
    plt.savefig(out_path, dpi=300, bbox_inches="tight")
    plt.close(fig)

    print(f"[BarChart] Saved comparative horizontal bar chart to: {out_path}")
    return out_path


def generate_bar_chart_for_tools(num_tools: int, phase: str = "phase3") -> Optional[str]:
    """Loads saved results from disk and generates the horizontal bar chart."""
    results = load_results_for_tools(num_tools, phase=phase)
    return generate_bar_chart_for_results(results, num_tools=num_tools, phase=phase)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate benchmark horizontal bar charts for an experiment scale")
    parser.add_argument("--tools", "-t", type=int, default=50, help="Number of tools (20, 30, 50, 100)")
    parser.add_argument("--phase", "-p", type=str, default="phase3", help="Experiment phase (default: phase3)")
    args = parser.parse_args()

    generate_bar_chart_for_tools(args.tools, phase=args.phase)
