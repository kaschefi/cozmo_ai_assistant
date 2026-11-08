import os
import json

base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../data/router_results'))
output_ts = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../frontend/src/features/bachelor-thesis/data/routerBenchmarkData.ts'))

phases = ['phase1', 'phase2', 'phase3']
tool_counts = [20, 30, 50, 100]

model_order = [
    "2-L-Laya-TopK",
    "2-L-Laya",
    "1-L-Laya-TopK",
    "1-L-Laya",
    "2-L-LLM",
    "Baseline-LLM"
]

canonical_map = {
    '1_l_laya': '1-L-Laya',
    '1-l-laya': '1-L-Laya',
    '1_l_laya_topk': '1-L-Laya-TopK',
    '1-l-laya-topk': '1-L-Laya-TopK',
    '2_l_laya': '2-L-Laya',
    '2-l-laya': '2-L-Laya',
    '2_l_laya_topk': '2-L-Laya-TopK',
    '2-l-laya-topk': '2-L-Laya-TopK',
    '2_l_llm': '2-L-LLM',
    '2-l-llm': '2-L-LLM',
    'baseline_llm': 'Baseline-LLM',
    'baseline-llm': 'Baseline-LLM',
}

# Distinct, high-contrast, non-confusable colors per model architecture
model_meta = {
    "2-L-Laya-TopK": {
        "color": "#F43F5E",      # Vibrant Rose / Crimson
        "badgeBg": "rgba(244, 63, 94, 0.15)",
        "badgeBorder": "rgba(244, 63, 94, 0.35)",
        "label": "2-L-Laya-TopK",
        "category": "Hybrid LAYA Router"
    },
    "2-L-Laya": {
        "color": "#F97316",      # Bright Tangerine Orange
        "badgeBg": "rgba(249, 115, 22, 0.15)",
        "badgeBorder": "rgba(249, 115, 22, 0.35)",
        "label": "2-L-Laya",
        "category": "Hybrid LAYA Router"
    },
    "1-L-Laya-TopK": {
        "color": "#10B981",      # Vivid Emerald Green
        "badgeBg": "rgba(16, 185, 129, 0.15)",
        "badgeBorder": "rgba(16, 185, 129, 0.35)",
        "label": "1-L-Laya-TopK",
        "category": "Direct LAYA Router"
    },
    "1-L-Laya": {
        "color": "#06B6D4",      # Electric Cyan / Aqua
        "badgeBg": "rgba(6, 182, 212, 0.15)",
        "badgeBorder": "rgba(6, 182, 212, 0.35)",
        "label": "1-L-Laya",
        "category": "Direct LAYA Router"
    },
    "2-L-LLM": {
        "color": "#A855F7",      # Vivid Purple / Violet
        "badgeBg": "rgba(168, 85, 247, 0.15)",
        "badgeBorder": "rgba(168, 85, 247, 0.35)",
        "label": "2-L-LLM",
        "category": "2-Layer LLM Router"
    },
    "Baseline-LLM": {
        "color": "#2563EB",      # Classic Royal Blue
        "badgeBg": "rgba(37, 99, 235, 0.15)",
        "badgeBorder": "rgba(37, 99, 235, 0.35)",
        "label": "Baseline-LLM",
        "category": "Monolithic Baseline"
    }
}

all_records = []

for phase in phases:
    for num_tools in tool_counts:
        tools_dir = os.path.join(base_dir, phase, f"{num_tools}_tools")
        if not os.path.exists(tools_dir):
            continue
        
        for fname in os.listdir(tools_dir):
            if not fname.endswith('.json'):
                continue
            
            fpath = os.path.join(tools_dir, fname)
            with open(fpath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            raw_id = data.get('model_id') or data.get('experiment_name', fname.replace('.json', ''))
            short = raw_id
            for prefix in [f'{num_tools}-Tools-', f'{num_tools}_Tools_', f'{num_tools}-tools-', f'{num_tools}_tools_']:
                short = short.replace(prefix, '')
            
            canonical_id = canonical_map.get(short.lower().replace('-', '_'), short)
            
            meta = model_meta.get(canonical_id, {
                "color": "#64748B",
                "badgeBg": "rgba(100, 116, 139, 0.15)",
                "badgeBorder": "rgba(100, 116, 139, 0.35)",
                "label": canonical_id,
                "category": "Other"
            })
            
            all_records.append({
                "modelId": canonical_id,
                "rawModelId": raw_id,
                "modelName": meta["label"],
                "color": meta["color"],
                "phase": phase,
                "numTools": num_tools,
                "accuracy": round(float(data.get("accuracy", 0)), 1),
                "correctCount": data.get("correct_count", 0),
                "totalCount": data.get("total_count", 0),
                "p50LatencyMs": round(float(data.get("p50_latency_ms", 0)), 1),
                "meanLatencyMs": round(float(data.get("mean_latency_ms", 0)), 1),
                "p90LatencyMs": round(float(data.get("p90_latency_ms", 0)), 1) if "p90_latency_ms" in data else None,
                "minLatencyMs": round(float(data.get("min_latency_ms", 0)), 1) if "min_latency_ms" in data else None,
                "maxLatencyMs": round(float(data.get("max_latency_ms", 0)), 1) if "max_latency_ms" in data else None,
                "totalTokens": int(data.get("total_tokens", 0)),
                "llmCallsCount": data.get("llm_calls_count", 0),
                "avgTokensPerCall": round(float(data.get("avg_tokens_per_call", 0)), 1) if "avg_tokens_per_call" in data else 0,
                "isLaya": "laya" in canonical_id.lower(),
                "description": data.get("description", "")
            })

os.makedirs(os.path.dirname(output_ts), exist_ok=True)

ts_content = f"""// Generated router benchmark dataset from backend/data/router_results
// Total evaluation records: {len(all_records)}

export type PhaseId = 'phase1' | 'phase2' | 'phase3';
export type ToolCount = 20 | 30 | 50 | 100;

export interface BenchmarkRecord {{
  modelId: string;
  rawModelId: string;
  modelName: string;
  color: string;
  phase: PhaseId;
  numTools: ToolCount;
  accuracy: number;
  correctCount: number;
  totalCount: number;
  p50LatencyMs: number;
  meanLatencyMs: number;
  p90LatencyMs: number | null;
  minLatencyMs: number | null;
  maxLatencyMs: number | null;
  totalTokens: number;
  llmCallsCount: number;
  avgTokensPerCall: number;
  isLaya: boolean;
  description: string;
}}

export interface ModelMetadata {{
  label: string;
  color: string;
  badgeBg: string;
  badgeBorder: string;
  category: string;
}}

export const MODEL_METADATA: Record<string, ModelMetadata> = {json.dumps(model_meta, indent=2)};

export const MODEL_DISPLAY_ORDER: string[] = {json.dumps(model_order, indent=2)};

export const AVAILABLE_PHASES: {{ id: PhaseId; label: string; description: string }}[] = [
  {{ id: 'phase1', label: 'Phase 1', description: 'Baseline prompt formulation & initial router configurations' }},
  {{ id: 'phase2', label: 'Phase 2', description: 'Refined tool descriptions & optimized FastEmbed thresholds' }},
  {{ id: 'phase3', label: 'Phase 3', description: 'Final production configurations with Top-k semantic clustering' }}
];

export const AVAILABLE_TOOL_COUNTS: ToolCount[] = [20, 30, 50, 100];

export const ROUTER_BENCHMARK_DATA: BenchmarkRecord[] = {json.dumps(all_records, indent=2)};

/**
 * Filter helper to retrieve records for a specific phase, tool count, and active model set.
 */
export function getFilteredBenchmarkRecords(
  phase: PhaseId,
  numTools: ToolCount,
  activeModels?: Set<string> | string[]
): BenchmarkRecord[] {{
  const activeSet = activeModels instanceof Set ? activeModels : activeModels ? new Set(activeModels) : null;
  
  const filtered = ROUTER_BENCHMARK_DATA.filter(
    (item) => item.phase === phase && item.numTools === numTools && (!activeSet || activeSet.has(item.modelId))
  );

  // Sort by canonical display order (from top to bottom in chart)
  return filtered.sort((a, b) => {{
    const idxA = MODEL_DISPLAY_ORDER.indexOf(a.modelId);
    const idxB = MODEL_DISPLAY_ORDER.indexOf(b.modelId);
    return (idxA !== -1 ? idxA : 99) - (idxB !== -1 ? idxB : 99);
  }});
}}

export interface ModelTrajectoryPoint {{
  numTools: ToolCount;
  accuracy: number;
  p50LatencyMs: number;
  meanLatencyMs: number;
  avgTokensPerCall: number;
  totalTokens: number;
  correctCount: number;
  totalCount: number;
}}

export interface ModelTrajectory {{
  modelId: string;
  modelName: string;
  color: string;
  category: string;
  isLaya: boolean;
  points: ModelTrajectoryPoint[];
}}

/**
 * Helper to retrieve scalability trajectories across all tool scales (20, 30, 50, 100)
 * for active models in a specific phase.
 */
export function getModelScalabilityTrajectories(
  phase: PhaseId,
  activeModels?: Set<string> | string[]
): ModelTrajectory[] {{
  const activeSet = activeModels instanceof Set ? activeModels : activeModels ? new Set(activeModels) : null;
  const models = MODEL_DISPLAY_ORDER.filter((m) => !activeSet || activeSet.has(m));

  return models.map((modelId) => {{
    const meta = MODEL_METADATA[modelId];
    const records = ROUTER_BENCHMARK_DATA.filter(
      (r) => r.phase === phase && r.modelId === modelId
    ).sort((a, b) => a.numTools - b.numTools);

    return {{
      modelId,
      modelName: meta?.label || modelId,
      color: meta?.color || '#3b82f6',
      category: meta?.category || 'Model',
      isLaya: modelId.toLowerCase().includes('laya'),
      points: records.map((r) => ({{
        numTools: r.numTools,
        accuracy: r.accuracy,
        p50LatencyMs: r.p50LatencyMs,
        meanLatencyMs: r.meanLatencyMs,
        avgTokensPerCall: r.avgTokensPerCall,
        totalTokens: r.totalTokens,
        correctCount: r.correctCount,
        totalCount: r.totalCount,
      }}))
    }};
  }});
}}
"""

with open(output_ts, 'w', encoding='utf-8') as f:
    f.write(ts_content)

print(f"Successfully generated {output_ts} with {len(all_records)} records.")
