import React, { useState, useMemo } from 'react';
import Header from '../../../shared/components/layout/Header';
import { useTheme } from '../../../shared/context/ThemeContext';
import {
  ConstellationFieldBackground,
  GoldVeinsBackground,
  ParticleDriftBackground
} from '../../../shared/components/backgrounds';
import {
  type PhaseId,
  type ToolCount,
  MODEL_DISPLAY_ORDER,
  getFilteredBenchmarkRecords,
  getModelScalabilityTrajectories
} from '../data/routerBenchmarkData';
import { RouterBarChart } from './RouterBarChart';
import { BenchmarkControlBar } from './BenchmarkControlBar';
import { RouterScalabilityLineChart } from './RouterScalabilityLineChart';
import { ScalabilityControlBar } from './ScalabilityControlBar';

export interface BachelorThesisPageProps {
  onBackToLanding?: () => void;
  onStartChat?: () => void;
}

/**
 * Bachelor Thesis - Router Model Benchmarks Page
 *
 * Dedicated evaluation platform presenting empirical benchmarks, token consumption,
 * latency, and routing accuracy across scaling tool sets (20 to 100 tools)
 * for the Moka AI Assistant bachelor thesis project.
 */
export const BachelorThesisPage: React.FC<BachelorThesisPageProps> = () => {
  const { theme } = useTheme();

  const isBlackIce = theme === 'black-ice';
  const isRoyal = theme === 'royal';
  const isIT = theme === 'it';

  // Benchmark Interactive Filter State (defaults to Phase 3 and 20 Tools per reference image)
  const [selectedPhase, setSelectedPhase] = useState<PhaseId>('phase3');
  const [selectedToolCount, setSelectedToolCount] = useState<ToolCount>(20);
  const [activeModels, setActiveModels] = useState<Set<string>>(
    () => new Set(MODEL_DISPLAY_ORDER)
  );

  // Default to publication view (matplotlib white) as requested to match the uploaded screenshot
  const [isChartDarkMode, setIsChartDarkMode] = useState<boolean>(false);

  // Filter records dynamically based on active phase, tool count, and selected models
  const filteredRecords = useMemo(() => {
    return getFilteredBenchmarkRecords(selectedPhase, selectedToolCount, activeModels);
  }, [selectedPhase, selectedToolCount, activeModels]);

  // Model selection handlers
  const handleToggleModel = (modelId: string) => {
    setActiveModels((prev) => {
      const next = new Set(prev);
      if (next.has(modelId)) {
        next.delete(modelId);
      } else {
        next.add(modelId);
      }
      return next;
    });
  };

  const handleSelectAllModels = () => {
    setActiveModels(new Set(MODEL_DISPLAY_ORDER));
  };

  const handleDeselectAllModels = () => {
    setActiveModels(new Set());
  };

  // Section 2: Scalability Line Chart state & trajectories
  const [lineChartPhase, setLineChartPhase] = useState<PhaseId>('phase3');
  const [lineChartActiveModels, setLineChartActiveModels] = useState<Set<string>>(
    () => new Set(MODEL_DISPLAY_ORDER)
  );
  const [lineChartLatencyMetric, setLineChartLatencyMetric] = useState<'mean' | 'p50'>('mean');
  const [isLineChartDarkMode, setIsLineChartDarkMode] = useState<boolean>(false);

  const scalabilityTrajectories = useMemo(() => {
    return getModelScalabilityTrajectories(lineChartPhase, lineChartActiveModels);
  }, [lineChartPhase, lineChartActiveModels]);

  const handleToggleLineModel = (modelId: string) => {
    setLineChartActiveModels((prev) => {
      const next = new Set(prev);
      if (next.has(modelId)) {
        next.delete(modelId);
      } else {
        next.add(modelId);
      }
      return next;
    });
  };

  const handleSelectAllLineModels = () => {
    setLineChartActiveModels(new Set(MODEL_DISPLAY_ORDER));
  };

  const handleDeselectAllLineModels = () => {
    setLineChartActiveModels(new Set());
  };

  // KPI Quick Highlights for active selection
  const kpis = useMemo(() => {
    if (filteredRecords.length === 0) return null;
    const sortedByAcc = [...filteredRecords].sort((a, b) => b.accuracy - a.accuracy);
    const sortedByMean = [...filteredRecords].sort((a, b) => a.meanLatencyMs - b.meanLatencyMs);
    const zeroTokenCount = filteredRecords.filter((r) => r.totalTokens === 0).length;

    return {
      bestAccuracy: sortedByAcc[0],
      lowestMeanModel: sortedByMean[0],
      zeroTokenRouters: zeroTokenCount
    };
  }, [filteredRecords]);

  return (
    <div className="relative min-h-screen w-full bg-[#03060a] text-slate-100 overflow-x-hidden select-none font-sans">
      {/* Dynamic theme-specific deep backdrop gradient */}
      <div 
        className="fixed inset-0 pointer-events-none transition-colors duration-700 z-0"
        style={{
          background: isBlackIce
            ? `
              radial-gradient(ellipse 90% 60% at 70% 30%, rgba(0, 243, 255, 0.12) 0%, rgba(8, 60, 77, 0.22) 35%, transparent 75%),
              radial-gradient(ellipse 60% 80% at 20% 80%, rgba(0, 243, 255, 0.06) 0%, rgba(6, 30, 42, 0.3) 40%, transparent 80%),
              linear-gradient(135deg, #020407 0%, #03080e 25%, #05141f 55%, #082836 85%, #061c27 100%)
            `
            : isRoyal
            ? `
              radial-gradient(ellipse 80% 60% at 75% 25%, rgba(212, 175, 55, 0.08) 0%, rgba(30, 25, 15, 0.25) 40%, transparent 75%),
              radial-gradient(ellipse 60% 70% at 25% 75%, rgba(255, 215, 0, 0.05) 0%, rgba(18, 16, 12, 0.3) 45%, transparent 80%),
              linear-gradient(135deg, #030407 0%, #06070b 30%, #0a0c12 65%, #020305 100%)
            `
            : isIT
            ? 'linear-gradient(180deg, #020503 0%, #030805 50%, #010402 100%)'
            : 'linear-gradient(180deg, #030407 0%, #05060a 50%, #020305 100%)'
        }}
      />

      {/* Shaders & Interactive Background Effects */}
      {isBlackIce && (
        <ConstellationFieldBackground className="fixed inset-0 pointer-events-none z-0" />
      )}
      {isRoyal && (
        <GoldVeinsBackground className="fixed inset-0 pointer-events-none z-0" />
      )}
      {isIT && (
        <ParticleDriftBackground className="fixed inset-0 pointer-events-none z-0" />
      )}

      {/* Digital Dot-matrix Grid Overlay */}
      <div
        className="fixed inset-0 pointer-events-none opacity-[0.035] z-[3]"
        style={{
          backgroundImage: isBlackIce 
            ? 'radial-gradient(circle, #00f3ff 1px, transparent 1px)' 
            : isRoyal
            ? 'radial-gradient(circle, rgba(212, 175, 55, 0.6) 1px, transparent 1px)'
            : isIT
            ? 'radial-gradient(circle, rgba(0, 255, 102, 0.6) 1px, transparent 1px)'
            : 'radial-gradient(circle, rgba(255, 255, 255, 0.4) 1px, transparent 1px)',
          backgroundSize: '28px 28px'
        }}
      />

      {/* 1. Global Navigation Header */}
      <Header defaultActive="bachelor-thesis" />

      {/* 2. Main Page Content */}
      <main className="relative z-10 w-full max-w-7xl mx-auto px-6 md:px-10 pt-28 md:pt-32 pb-28 flex flex-col gap-10">
        
        {/* Hero Section */}
        <div className="flex flex-col gap-4 border-b border-white/[0.08] pb-8">
          <div className="flex flex-wrap items-center gap-3">
            <span className="px-3 py-1 rounded-full text-xs font-mono font-medium tracking-wider uppercase bg-cyan-950/60 border border-cyan-800/50 text-cyan-400">
              Bachelor Thesis
            </span>
            <span className="text-xs font-mono text-slate-400">
              Routing-Strukturen für große Tool-Mengen
            </span>
            <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-white/[0.06] text-slate-300">
              72 Benchmark Experiments
            </span>
          </div>

          <h1 className="text-3xl md:text-5xl font-extrabold tracking-tight text-white">
            Router Models Benchmark Suite
          </h1>

          <p className="text-base md:text-lg text-slate-400 max-w-4xl leading-relaxed">
            Empirical comparative analysis across three router architectures: Monolithic Baseline LLM, 2-Layer LLM (FastEmbed + FAISS Top-k), and LAYA Typed Decisions across scaling tool sets (20, 30, 50, and 100 tools).
          </p>
        </div>

        {/* Quick KPI Overview Highlights */}
        {kpis && (
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            {/* Top Accuracy */}
            <div className="p-4 rounded-xl border border-white/[0.08] bg-black/40 backdrop-blur-md flex flex-col gap-1">
              <span className="text-[11px] font-mono text-slate-400 uppercase tracking-wider">Top Accuracy Leader</span>
              <div className="flex items-baseline justify-between">
                <span className="text-lg font-bold text-white truncate">{kpis.bestAccuracy.modelName}</span>
                <span className="text-lg font-mono font-bold text-emerald-400">{kpis.bestAccuracy.accuracy}%</span>
              </div>
              <span className="text-[11px] text-slate-400">
                {kpis.bestAccuracy.correctCount}/{kpis.bestAccuracy.totalCount} tests passed
              </span>
            </div>

            {/* Lowest Mean Latency */}
            <div className="p-4 rounded-xl border border-white/[0.08] bg-black/40 backdrop-blur-md flex flex-col gap-1">
              <span className="text-[11px] font-mono text-slate-400 uppercase tracking-wider">Lowest Mean Latency</span>
              <div className="flex items-baseline justify-between">
                <span className="text-lg font-bold text-white truncate">{kpis.lowestMeanModel.modelName}</span>
                <span className="text-lg font-mono font-bold text-cyan-400">{Math.round(kpis.lowestMeanModel.meanLatencyMs)}ms</span>
              </div>
              <span className="text-[11px] text-slate-400">
                Median (P50): {Math.round(kpis.lowestMeanModel.p50LatencyMs)}ms
              </span>
            </div>

            {/* Zero Token Efficiency */}
            <div className="p-4 rounded-xl border border-white/[0.08] bg-black/40 backdrop-blur-md flex flex-col gap-1">
              <span className="text-[11px] font-mono text-slate-400 uppercase tracking-wider">Zero-Token Evaluators</span>
              <div className="flex items-baseline justify-between">
                <span className="text-lg font-bold text-white truncate">LAYA Models</span>
                <span className="text-lg font-mono font-bold text-purple-400">{kpis.zeroTokenRouters} Models</span>
              </div>
              <span className="text-[11px] text-slate-400">
                0 LLM tokens required for decision
              </span>
            </div>
          </div>
        )}

        {/* =========================================================================
            SECTION 1: COMPARATIVE HORIZONTAL BAR CHART
           ========================================================================= */}
        <section className="flex flex-col gap-5">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2.5">
              <div className="w-2.5 h-2.5 rounded-full bg-cyan-400" />
              <h2 className="text-lg md:text-xl font-bold text-white tracking-wide">
                Single-Scale Comparative Benchmark
              </h2>
            </div>
            <span className="text-xs font-mono text-slate-400">
              Showing {filteredRecords.length} Active Models
            </span>
          </div>

          {/* 3-Panel Horizontal Bar Chart */}
          <RouterBarChart
            records={filteredRecords}
            phase={selectedPhase}
            numTools={selectedToolCount}
            isDarkMode={isChartDarkMode}
          />

          {/* Interactive Controls Bar Directly Under the Chart */}
          <BenchmarkControlBar
            selectedPhase={selectedPhase}
            onSelectPhase={setSelectedPhase}
            selectedToolCount={selectedToolCount}
            onSelectToolCount={setSelectedToolCount}
            activeModels={activeModels}
            onToggleModel={handleToggleModel}
            onSelectAllModels={handleSelectAllModels}
            onDeselectAllModels={handleDeselectAllModels}
            isDarkMode={isChartDarkMode}
            onToggleDarkMode={() => setIsChartDarkMode(!isChartDarkMode)}
          />
        </section>

        {/* =========================================================================
            SECTION 2: 4-PANEL SCALABILITY LINE CHART (20 → 100 TOOLS)
           ========================================================================= */}
        <section className="mt-8 pt-8 border-t border-white/[0.08] flex flex-col gap-5">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2.5">
              <div className="w-2.5 h-2.5 rounded-full bg-purple-400" />
              <h2 className="text-lg md:text-xl font-bold text-white tracking-wide">
                Multi-Scale Scalability Trajectories
              </h2>
            </div>
            <span className="text-xs font-mono text-purple-400/90">
              Comparing {scalabilityTrajectories.length} Model Trajectories (20 → 100 Tools)
            </span>
          </div>

          {/* 4-Panel Line Chart Component */}
          <RouterScalabilityLineChart
            trajectories={scalabilityTrajectories}
            phase={lineChartPhase}
            latencyMetric={lineChartLatencyMetric}
            isDarkMode={isLineChartDarkMode}
          />

          {/* Interactive Controls Bar for Line Chart */}
          <ScalabilityControlBar
            selectedPhase={lineChartPhase}
            onSelectPhase={setLineChartPhase}
            activeModels={lineChartActiveModels}
            onToggleModel={handleToggleLineModel}
            onSelectAllModels={handleSelectAllLineModels}
            onDeselectAllModels={handleDeselectAllLineModels}
            latencyMetric={lineChartLatencyMetric}
            onSelectLatencyMetric={setLineChartLatencyMetric}
            isDarkMode={isLineChartDarkMode}
            onToggleDarkMode={() => setIsLineChartDarkMode(!isLineChartDarkMode)}
          />
        </section>

      </main>
    </div>
  );
};

export default BachelorThesisPage;
