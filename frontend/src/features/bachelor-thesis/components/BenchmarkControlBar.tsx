import React, { useState, useRef, useEffect } from 'react';
import {
  type PhaseId,
  type ToolCount,
  AVAILABLE_PHASES,
  AVAILABLE_TOOL_COUNTS,
  MODEL_DISPLAY_ORDER,
  MODEL_METADATA
} from '../data/routerBenchmarkData';

export interface BenchmarkControlBarProps {
  selectedPhase: PhaseId;
  onSelectPhase: (phase: PhaseId) => void;
  selectedToolCount: ToolCount;
  onSelectToolCount: (count: ToolCount) => void;
  activeModels: Set<string>;
  onToggleModel: (modelId: string) => void;
  onSelectAllModels: () => void;
  onDeselectAllModels: () => void;
  isDarkMode: boolean;
  onToggleDarkMode: () => void;
}

/**
 * BenchmarkControlBar Component
 *
 * Controls placed directly below the horizontal bar chart:
 * 1. Phase Selector (Phase 1, 2, 3)
 * 2. Tool Number Selector (20, 30, 50, 100 tools)
 * 3. Models Dropdown with On/Off toggles per model
 * 4. Chart View Theme Mode (Publication Light vs Dark Glass)
 */
export const BenchmarkControlBar: React.FC<BenchmarkControlBarProps> = ({
  selectedPhase,
  onSelectPhase,
  selectedToolCount,
  onSelectToolCount,
  activeModels,
  onToggleModel,
  onSelectAllModels,
  onDeselectAllModels,
  isDarkMode,
  onToggleDarkMode,
}) => {
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Close dropdown on outside click
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setDropdownOpen(false);
      }
    };
    if (dropdownOpen) {
      document.addEventListener('mousedown', handleClickOutside);
    }
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [dropdownOpen]);

  const activeCount = activeModels.size;
  const totalModels = MODEL_DISPLAY_ORDER.length;

  return (
    <div className="w-full flex flex-col gap-5 p-6 rounded-2xl border border-white/[0.08] bg-black/40 backdrop-blur-xl shadow-2xl">
      {/* Top Controls Grid */}
      <div className="grid grid-cols-1 md:grid-cols-12 gap-6 items-center">
        
        {/* 1. Phase Selector (col 1-4) */}
        <div className="md:col-span-4 flex flex-col gap-2">
          <label className="text-xs font-mono font-semibold uppercase tracking-wider text-slate-400 flex items-center gap-2">
            <span>Evaluation Phase</span>
            <span className="text-[10px] text-cyan-400 font-mono">({selectedPhase})</span>
          </label>
          <div className="flex rounded-xl bg-black/50 border border-white/[0.08] p-1 gap-1">
            {AVAILABLE_PHASES.map((p) => {
              const isActive = selectedPhase === p.id;
              return (
                <button
                  key={p.id}
                  type="button"
                  onClick={() => onSelectPhase(p.id)}
                  className={`flex-1 py-2 px-3 rounded-lg text-xs font-semibold transition-all duration-200 cursor-pointer ${
                    isActive
                      ? 'bg-gradient-to-r from-cyan-500 to-blue-600 text-white shadow-lg shadow-cyan-500/20'
                      : 'text-slate-400 hover:text-white hover:bg-white/[0.05]'
                  }`}
                  title={p.description}
                >
                  {p.label}
                </button>
              );
            })}
          </div>
        </div>

        {/* 2. Tool Number Selector (col 5-8) */}
        <div className="md:col-span-4 flex flex-col gap-2">
          <label className="text-xs font-mono font-semibold uppercase tracking-wider text-slate-400 flex items-center gap-2">
            <span>Tool Scale Size</span>
            <span className="text-[10px] text-emerald-400 font-mono">({selectedToolCount} Tools)</span>
          </label>
          <div className="flex rounded-xl bg-black/50 border border-white/[0.08] p-1 gap-1">
            {AVAILABLE_TOOL_COUNTS.map((tc) => {
              const isActive = selectedToolCount === tc;
              return (
                <button
                  key={tc}
                  type="button"
                  onClick={() => onSelectToolCount(tc)}
                  className={`flex-1 py-2 px-2.5 rounded-lg text-xs font-semibold transition-all duration-200 cursor-pointer ${
                    isActive
                      ? 'bg-gradient-to-r from-emerald-500 to-teal-600 text-white shadow-lg shadow-emerald-500/20'
                      : 'text-slate-400 hover:text-white hover:bg-white/[0.05]'
                  }`}
                >
                  {tc} Tools
                </button>
              );
            })}
          </div>
        </div>

        {/* 3. Models Dropdown Filter & Chart View Mode (col 9-12) */}
        <div className="md:col-span-4 flex flex-col gap-2">
          <label className="text-xs font-mono font-semibold uppercase tracking-wider text-slate-400 flex items-center justify-between">
            <span>Model Filters</span>
            <span className="text-[10px] text-purple-400 font-mono">
              {activeCount} of {totalModels} Active
            </span>
          </label>

          <div className="flex items-center gap-2">
            {/* Dropdown Trigger */}
            <div className="relative flex-1" ref={dropdownRef}>
              <button
                type="button"
                onClick={() => setDropdownOpen(!dropdownOpen)}
                className="w-full flex items-center justify-between py-2 px-3.5 rounded-xl bg-black/50 border border-white/[0.08] hover:border-white/[0.2] text-xs font-semibold text-slate-200 transition-all cursor-pointer"
              >
                <div className="flex items-center gap-2 truncate">
                  <div className="w-2 h-2 rounded-full bg-cyan-400 animate-pulse" />
                  <span>Models ({activeCount}/{totalModels})</span>
                </div>
                <svg
                  className={`w-4 h-4 text-slate-400 transition-transform duration-200 ${dropdownOpen ? 'rotate-180' : ''}`}
                  viewBox="0 0 20 20"
                  fill="currentColor"
                >
                  <path fillRule="evenodd" d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z" clipRule="evenodd" />
                </svg>
              </button>

              {/* Dropdown Menu Modal */}
              {dropdownOpen && (
                <div className="absolute right-0 bottom-full mb-2 w-72 md:w-80 rounded-xl bg-[#090d16] border border-white/[0.15] shadow-2xl p-3 z-50 flex flex-col gap-2.5 backdrop-blur-2xl">
                  {/* Dropdown header with quick action buttons */}
                  <div className="flex items-center justify-between pb-2 border-b border-white/[0.08] text-xs">
                    <span className="font-semibold text-white">Toggle Router Models</span>
                    <div className="flex items-center gap-2 font-mono">
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
                  </div>

                  {/* List of Models with On/Off switches */}
                  <div className="flex flex-col gap-1.5 max-h-72 overflow-y-auto pr-1">
                    {MODEL_DISPLAY_ORDER.map((modelId) => {
                      const meta = MODEL_METADATA[modelId];
                      const isChecked = activeModels.has(modelId);

                      return (
                        <div
                          key={modelId}
                          onClick={() => onToggleModel(modelId)}
                          className={`flex items-center justify-between p-2 rounded-lg cursor-pointer transition-colors ${
                            isChecked
                              ? 'bg-white/[0.04] hover:bg-white/[0.08]'
                              : 'opacity-50 hover:opacity-80 hover:bg-white/[0.02]'
                          }`}
                        >
                          <div className="flex items-center gap-2.5 min-w-0">
                            {/* Color indicator pip */}
                            <span
                              className="w-3 h-3 rounded-sm flex-none shadow-sm"
                              style={{ backgroundColor: meta?.color || '#3b82f6' }}
                            />
                            <div className="flex flex-col min-w-0">
                              <span className="text-xs font-bold text-white truncate">
                                {meta?.label || modelId}
                              </span>
                              <span className="text-[10px] text-slate-400 truncate">
                                {meta?.category || 'Model'}
                              </span>
                            </div>
                          </div>

                          {/* Accessible Toggle Switch */}
                          <div
                            className={`w-8 h-4.5 rounded-full p-0.5 transition-colors duration-200 flex items-center ${
                              isChecked ? 'bg-cyan-500 justify-end' : 'bg-slate-700 justify-start'
                            }`}
                          >
                            <div className="w-3.5 h-3.5 rounded-full bg-white shadow-md transform transition-transform" />
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}
            </div>

            {/* Publication White vs Dark Studio Toggle */}
            <button
              type="button"
              onClick={onToggleDarkMode}
              className={`py-2 px-3 rounded-xl border text-xs font-semibold flex items-center gap-1.5 transition-all cursor-pointer ${
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
        <span className="text-[11px] font-mono text-slate-400 mr-1">Active Models:</span>
        {MODEL_DISPLAY_ORDER.map((modelId) => {
          const meta = MODEL_METADATA[modelId];
          const isChecked = activeModels.has(modelId);

          return (
            <button
              key={modelId}
              type="button"
              onClick={() => onToggleModel(modelId)}
              className={`inline-flex items-center gap-1.5 py-1 px-2.5 rounded-lg text-xs font-semibold border transition-all cursor-pointer ${
                isChecked
                  ? 'border-white/[0.15] text-white shadow-sm'
                  : 'border-white/[0.04] text-slate-500 bg-transparent line-through opacity-50'
              }`}
              style={{
                backgroundColor: isChecked ? (meta?.badgeBg || 'rgba(255,255,255,0.06)') : 'transparent',
                borderColor: isChecked ? (meta?.badgeBorder || 'rgba(255,255,255,0.2)') : 'transparent'
              }}
            >
              <span
                className="w-2 h-2 rounded-full"
                style={{ backgroundColor: meta?.color || '#3b82f6' }}
              />
              <span>{meta?.label || modelId}</span>
            </button>
          );
        })}
      </div>
    </div>
  );
};

export default BenchmarkControlBar;
