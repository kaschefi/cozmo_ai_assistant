# backend/test/routers/saver.py
"""
Benchmark Results Saver and Manager for Router Evaluations.

Saves benchmark evaluation results as structured JSON files into:
`backend/data/router results/<phase>/<scale>_tools/<model_name>.json`
(e.g., `backend/data/router results/phase1/20_tools/2_L_LLM.json`).
"""

import os
import sys
import json
import re
from datetime import datetime
from typing import Dict, Any, List, Optional

# Ensure backend directory is in path
backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)


def clean_model_filename(raw_name: str) -> str:
    """
    Cleans model identifier by stripping scale prefixes like '20-Tools-', '50_Tools_', etc.,
    and formatting as requested (e.g., '2_L_llm', '2_L_Laya_TopK', 'Baseline_LLM').
    Examples:
      '20-Tools-2-L-LLM' -> '2_L_LLM'
      '50-Tools-1-L-Laya-TopK' -> '1_L_Laya_TopK'
      '20-Tools-Baseline-LLM' -> 'Baseline_LLM'
    """
    # Remove any scale pattern like '20-Tools-', '20_tools_', etc.
    cleaned = re.sub(r"^\d+[\-_]tools?[\-_]", "", raw_name, flags=re.IGNORECASE)
    # Replace hyphens with underscores
    cleaned = cleaned.replace("-", "_").replace(" ", "_")
    return cleaned


def get_results_dir(phase: str = "phase3", num_tools: Optional[int] = None) -> str:
    """
    Returns the absolute path to:
    - `backend/data/router results/<phase>/<num_tools>_tools` if num_tools is provided
    - `backend/data/router results/<phase>` if num_tools is None.
    Creates directories if they do not exist.
    """
    if num_tools is not None:
        target_dir = os.path.join(backend_path, "data", "router results", phase, f"{num_tools}_tools")
    else:
        target_dir = os.path.join(backend_path, "data", "router results", phase)
    os.makedirs(target_dir, exist_ok=True)
    return target_dir


def save_experiment_result(
    result_data: Dict[str, Any],
    num_tools: int,
    phase: str = "phase3",
    custom_filename: Optional[str] = None
) -> str:
    """
    Saves a single router experiment result dictionary into:
    `backend/data/router results/<phase>/<num_tools>_tools/<model_name>.json`.
    
    Returns:
        The absolute path to the saved JSON file.
    """
    target_dir = get_results_dir(phase, num_tools=num_tools)
    model_id = result_data.get("experiment_name", "Unknown")

    if custom_filename:
        filename = custom_filename if custom_filename.endswith(".json") else f"{custom_filename}.json"
    else:
        clean_name = clean_model_filename(model_id)
        filename = f"{clean_name}.json"

    file_path = os.path.join(target_dir, filename)

    if "saved_at" not in result_data:
        result_data["saved_at"] = datetime.now().isoformat()
    result_data["phase"] = phase
    result_data["num_tools"] = num_tools

    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(result_data, f, indent=2, ensure_ascii=False)

    print(f"[Saver] Saved benchmark result to: {file_path}")
    return file_path


def load_all_results_for_phase(phase: str = "phase3") -> List[Dict[str, Any]]:
    """
    Recursively loads all JSON benchmark result files from `backend/data/router results/<phase>`.
    Walks through all experiment subfolders (e.g. `20_tools`, `30_tools`, `50_tools`, `100_tools`).
    """
    base_phase_dir = get_results_dir(phase, num_tools=None)
    results = []
    if not os.path.exists(base_phase_dir):
        return results

    for root, _, files in os.walk(base_phase_dir):
        for fname in files:
            if fname.endswith(".json"):
                fpath = os.path.join(root, fname)
                try:
                    with open(fpath, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        results.append(data)
                except Exception as e:
                    print(f"[Saver] Warning: could not parse {fpath}: {e}")

    return results


def load_results_for_tools(num_tools: int, phase: str = "phase3") -> List[Dict[str, Any]]:
    """
    Loads all results for a specific tools scale (e.g. 20, 30, 50, 100) from:
    `backend/data/router results/<phase>/<num_tools>_tools/` or matching phase files.
    """
    # First check dedicated subfolder
    subfolder = get_results_dir(phase, num_tools=num_tools)
    results = []
    if os.path.exists(subfolder):
        for fname in os.listdir(subfolder):
            if fname.endswith(".json"):
                fpath = os.path.join(subfolder, fname)
                try:
                    with open(fpath, "r", encoding="utf-8") as f:
                        results.append(json.load(f))
                except Exception as e:
                    print(f"[Saver] Warning: could not parse {fpath}: {e}")

    if results:
        return results

    # Fallback to scanning whole phase
    all_results = load_all_results_for_phase(phase)
    return [r for r in all_results if r.get("num_tools") == num_tools]
