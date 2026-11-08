import React from 'react';
import { useDockMagnification } from '../../../shared/hooks';
import {
  type PhaseId,
  AVAILABLE_PHASES,
  MODEL_DISPLAY_ORDER,
  MODEL_METADATA
} from '../data/routerBenchmarkData';

export interface ScalabilityControlBarProps {
  selectedPhase: PhaseId;
  onSelectPhase: (phase: PhaseId) => void;
  activeModels: Set<string>;
  onToggleModel: (modelId: string) => void;
  onSelectAllModels: () => void;
  onDeselectAllModels: () => void;
  latencyMetric: 'mean' | 'p50';
  onSelectLatencyMetric: (metric: 'mean' | 'p50') => void;
  isDarkMode: boolean;
  onToggleDarkMode: () => void;
  // Cross-Phase Comparison Mode Props
  isCrossPhaseMode: boolean;
  onToggleCrossPhaseMode: () => void;
  crossPhaseModel: string;
  onSelectCrossPhaseModel: (modelId: string) => void;
}

/**
 * ScalabilityControlBar Component
 *
 * Dedicated interactive controls directly below the 4-panel Scalability Line Chart:
 * 1. Phase Selector (Phase 1, 2, 3) - exits 3-phase mode when a single phase is clicked
 * 2. Latency Metric Selector (Mean vs P50)
 * 3. 3-Phase Comparison Toggle Button & Publication Light/Dark Studio Mode Toggle
 * 4. Model Selection Chips (multi-select in standard mode, single-model picker in 3-phase comparison mode)
 */
export const ScalabilityControlBar: React.FC<ScalabilityControlBarProps> = ({
  selectedPhase,
  onSelectPhase,
  activeModels,
  onToggleModel,
  onSelectAllModels,
  onDeselectAllModels,
  latencyMetric,
  onSelectLatencyMetric,
  isDarkMode,
  onToggleDarkMode,
  isCrossPhaseMode,
  onToggleCrossPhaseMode,
  crossPhaseModel,
  onSelectCrossPhaseModel,
}) => {
  const activeCount = activeModels.size;
  const totalModels = MODEL_DISPLAY_ORDER.length;

  const phaseDockRef = useDockMagnification<HTMLDivElement>({ proximity: 90, popDistance: 3.5, scaleGrowth: 0.03 });
  const metricDockRef = useDockMagnification<HTMLDivElement>({ proximity: 85, popDistance: 3.5, scaleGrowth: 0.03 });

  return (
    <div className="w-full flex flex-col gap-5 p-6 rounded-2xl border border-white/[0.08] bg-black/40 backdrop-blur-xl shadow-2xl">
      {/* Top Controls Grid */}
      <div className="grid grid-cols-1 md:grid-cols-12 gap-6 items-center">
        
        {/* 1. Phase Selector (col 1-4) */}
        <div className="md:col-span-4 flex flex-col gap-2">
          <label className="text-xs font-mono font-semibold uppercase tracking-wider text-slate-400 flex items-center justify-between">
            <span className="flex items-center gap-2">
              <span>Evaluation Phase</span>
              {isCrossPhaseMode ? (
                <span className="text-[10px] text-slate-400 font-mono font-bold">
                  (Phases 1, 2, 3 Active)
                </span>
              ) : (
                <span className="text-[10px] text-slate-400 font-mono">({selectedPhase.toUpperCase()})</span>
              )}
            </span>
          </label>
          <div ref={phaseDockRef} className="flex rounded-xl bg-[#08080c]/85 border border-white/[0.08] p-1 gap-1 backdrop-blur-xl shadow-lg overflow-visible">
            {AVAILABLE_PHASES.map((p) => {
              const isActive = !isCrossPhaseMode && selectedPhase === p.id;
              return (
                <button
                  key={p.id}
                  data-dock-item
                  type="button"
                  onClick={() => {
                    if (isCrossPhaseMode) {
                      onToggleCrossPhaseMode();
                    }
                    onSelectPhase(p.id);
                  }}
                  aria-pressed={isActive}
                  className={`flex-1 py-2 px-3 rounded-lg text-xs transition-colors duration-150 cursor-pointer ${
                    isActive
                      ? 'bg-white text-[#09090b] font-bold border border-white shadow-[0_4px_14px_rgba(255,255,255,0.18)]'
                      : 'text-slate-400 hover:text-white hover:bg-white/[0.08] border border-transparent font-medium'
                  }`}
                  title={isCrossPhaseMode ? `Exit 3-Phase mode and switch to ${p.label}` : p.description}
                >
                  {p.label}
                </button>
              );
            })}
          </div>
        </div>

        {/* 2. Latency Metric Toggle (col 5-8) */}
        <div className="md:col-span-4 flex flex-col gap-2">
          <label className="text-xs font-mono font-semibold uppercase tracking-wider text-slate-400 flex items-center gap-2">
            <span>Latency Metric</span>
            <span className="text-[10px] text-slate-400 font-mono">
              ({latencyMetric === 'mean' ? 'MEAN LATENCY' : 'P50 MEDIAN'})
            </span>
          </label>
          <div ref={metricDockRef} className="flex rounded-xl bg-[#08080c]/85 border border-white/[0.08] p-1 gap-1 backdrop-blur-xl shadow-lg overflow-visible">
            <button
              data-dock-item
              type="button"
              onClick={() => onSelectLatencyMetric('mean')}
              aria-pressed={latencyMetric === 'mean'}
              className={`flex-1 py-2 px-3 rounded-lg text-xs transition-colors duration-150 cursor-pointer ${
                latencyMetric === 'mean'
                  ? 'bg-white text-[#09090b] font-bold border border-white shadow-[0_4px_14px_rgba(255,255,255,0.18)]'
                  : 'text-slate-400 hover:text-white hover:bg-white/[0.08] border border-transparent font-medium'
              }`}
            >
              Mean (Average)
            </button>
            <button
              data-dock-item
              type="button"
              onClick={() => onSelectLatencyMetric('p50')}
              aria-pressed={latencyMetric === 'p50'}
              className={`flex-1 py-2 px-3 rounded-lg text-xs transition-colors duration-150 cursor-pointer ${
                latencyMetric === 'p50'
                  ? 'bg-white text-[#09090b] font-bold border border-white shadow-[0_4px_14px_rgba(255,255,255,0.18)]'
                  : 'text-slate-400 hover:text-white hover:bg-white/[0.08] border border-transparent font-medium'
              }`}
            >
              P50 (Median)
            </button>
          </div>
        </div>

        {/* 3. Cross-Phase Toggle & Publication Theme Toggle (col 9-12) */}
        <div className="md:col-span-4 flex flex-col gap-2">
          <label className="text-xs font-mono font-semibold uppercase tracking-wider text-slate-400 flex items-center justify-between">
            <span>Analysis Mode</span>
            <span className={`text-[10px] font-mono ${isCrossPhaseMode ? 'text-amber-400 font-semibold' : 'text-purple-400'}`}>
              {isCrossPhaseMode ? 'All 3 Phases' : `${activeCount}/${totalModels} Models`}
            </span>
          </label>

          <div className="flex items-center gap-2">
            {/* Compare All 3 Phases Button */}
            <button
              type="button"
              onClick={onToggleCrossPhaseMode}
              className={`flex-1 py-2 px-3.5 rounded-xl border text-xs font-semibold flex items-center justify-center gap-2 transition-all cursor-pointer ${
                isCrossPhaseMode
                  ? 'bg-gradient-to-r from-amber-500 via-rose-500 to-purple-600 border-amber-400/50 text-white shadow-lg shadow-purple-500/25 ring-2 ring-purple-500/30 font-bold'
                  : 'bg-black/50 border-white/[0.08] hover:border-purple-500/40 hover:bg-white/[0.05] text-slate-200'
              }`}
              title="Compare the selected model across all 3 evaluation phases simultaneously on the line chart"
            >
              <svg className="w-3.5 h-3.5 flex-none" viewBox="0 0 20 20" fill="currentColor">
                <path d="M2 11a1 1 0 011-1h2a1 1 0 011 1v5a1 1 0 01-1 1H3a1 1 0 01-1-1v-5zM8 7a1 1 0 011-1h2a1 1 0 011 1v9a1 1 0 01-1 1H9a1 1 0 01-1-1V7zM14 4a1 1 0 011-1h2a1 1 0 011 1v12a1 1 0 01-1 1h-2a1 1 0 01-1-1V4z" />
              </svg>
              <span>{isCrossPhaseMode ? 'Comparing 3 Phases' : 'Compare All 3 Phases'}</span>
            </button>

            {/* Publication White vs Dark Studio Toggle */}
            <button
              type="button"
              onClick={onToggleDarkMode}
              className={`py-2 px-3 rounded-xl border text-xs font-semibold flex items-center gap-1.5 transition-all cursor-pointer flex-none ${
                isDarkMode
                  ? 'bg-white/[0.05] border-white/[0.1] text-slate-300 hover:text-white'
                  : 'bg-white text-slate-900 border-slate-300 shadow-md font-bold'
              }`}
              title="Toggle Chart Publication View (Matplotlib White vs Dark Mode)"
            >
              {isDarkMode ? (
                <>
                  <svg className="w-3.5 h-3.5 text-cyan-400" viewBox="0 0 20 20" fill="currentColor">
                    <path d="M17.293 13.293A8 8 0 016.707 2.707a8.001 8.001 0 1010.586 10.586z" />
                  </svg>
                  <span>Dark</span>
                </>
              ) : (
                <>
                  <svg className="w-3.5 h-3.5 text-amber-500" viewBox="0 0 20 20" fill="currentColor">
                    <path fillRule="evenodd" d="M10 2a1 1 0 011 1v1a1 1 0 11-2 0V3a1 1 0 011-1zm4 8a4 4 0 11-8 0 4 4 0 018 0zm-.464 4.95l.707.707a1 1 0 001.414-1.414l-.707-.707a1 1 0 00-1.414 1.414zm2.12-10.607a1 1 0 010 1.414l-.706.707a1 1 0 11-1.414-1.414l.707-.707a1 1 0 011.414 0zM17 11a1 1 0 100-2h-1a1 1 0 100 2h1zm-7 4a1 1 0 011 1v1a1 1 0 11-2 0v-1a1 1 0 011-1zM5.05 6.464A1 1 0 106.465 5.05l-.708-.707a1 1 0 00-1.414 1.414l.707.707zm1.414 8.486l-.707.707a1 1 0 01-1.414-1.414l.707-.707a1 1 0 011.414 1.414zM4 11a1 1 0 100-2H3a1 1 0 000 2h1z" clipRule="evenodd" />
                  </svg>
                  <span>Light</span>
                </>
              )}
            </button>
          </div>
        </div>
      </div>

      {/* Quick Model Toggle Chips Bar */}
      <div className="flex flex-wrap items-center gap-2 pt-3 border-t border-white/[0.06]">
        <span className="text-[11px] font-mono text-slate-400 mr-1">
          {isCrossPhaseMode ? 'Select Model (Compare 3 Phases):' : 'Active Trajectories:'}
        </span>
        {MODEL_DISPLAY_ORDER.map((modelId) => {
          const meta = MODEL_METADATA[modelId];
          const isSelected = isCrossPhaseMode
            ? crossPhaseModel === modelId
            : activeModels.has(modelId);

          return (
            <button
              key={modelId}
              type="button"
              onClick={() => {
                if (isCrossPhaseMode) {
                  onSelectCrossPhaseModel(modelId);
                } else {
                  onToggleModel(modelId);
                }
              }}
              className={`inline-flex items-center gap-1.5 py-1 px-2.5 rounded-lg text-xs font-semibold border transition-all cursor-pointer ${
                isSelected
                  ? 'border-white/[0.2] text-white shadow-sm ring-1 ring-white/20'
                  : 'border-white/[0.04] text-slate-500 bg-transparent opacity-50 hover:opacity-80'
              }`}
              style={{
                backgroundColor: isSelected ? (meta?.badgeBg || 'rgba(255,255,255,0.06)') : 'transparent',
                borderColor: isSelected ? (meta?.badgeBorder || 'rgba(255,255,255,0.2)') : 'transparent'
              }}
            >
              <span
                className={`w-2 h-2 rounded-full ${isSelected && isCrossPhaseMode ? 'animate-pulse' : ''}`}
                style={{ backgroundColor: meta?.color || '#3b82f6' }}
              />
              <span>{meta?.label || modelId}</span>
              {isCrossPhaseMode && isSelected && (
                <span className="text-[9px] uppercase tracking-wider font-mono px-1 py-0.2 rounded bg-amber-500/20 text-amber-300 ml-1">
                  Active
                </span>
              )}
            </button>
          );
        })}

        {/* Quick All / None action links when in standard multi-model mode */}
        {!isCrossPhaseMode && (
          <div className="flex items-center gap-2 ml-auto text-xs font-mono">
            <button
              type="button"
              onClick={onSelectAllModels}
              className="text-[11px] text-cyan-400 hover:underline cursor-pointer"
            >
              All
            </button>
            <span className="text-slate-600">•</span>
            <button
              type="button"
              onClick={onDeselectAllModels}
              className="text-[11px] text-rose-400 hover:underline cursor-pointer"
            >
              None
            </button>
          </div>
        )}
      </div>
    </div>
  );
};

export default ScalabilityControlBar;
