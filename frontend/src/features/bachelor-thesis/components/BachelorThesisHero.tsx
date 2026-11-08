import React, { useState, useEffect } from 'react';
import type { BenchmarkRecord, PhaseId, ToolCount } from '../data/routerBenchmarkData';
import { PHASE_METADATA } from '../data/routerBenchmarkData';

export interface BachelorThesisHeroKPIs {
  bestAccuracy: BenchmarkRecord;
  lowestMeanModel: BenchmarkRecord;
  zeroTokenRouters: number;
  baselineModel?: BenchmarkRecord;
}

export interface BachelorThesisHeroProps {
  selectedPhase: PhaseId;
  selectedToolCount: ToolCount;
  kpis: BachelorThesisHeroKPIs | null;
  onJumpToSection?: (sectionId: string) => void;
}

/**
 * BachelorThesisHero Component
 *
 * Side-by-side layout matching the Home Page ProjectIntro architecture:
 * - Viewport-framed height ensuring only the hero is visible at scroll 0
 * - Generous top breathing room below the fixed navigation dock
 * - Expanded spacing between the content/cards and the bottom shortcut bar
 * - Left column: Signature Megrim title with brand underline & thesis narrative
 * - Right column: 3 stacked frosted glass KPI telemetry cards with icon boxes
 * - Bottom ribbon: Independent floating navigation buttons that pop up on hover
 *   and switch to solid white when clicked or active, without being connected together.
 */
export const BachelorThesisHero: React.FC<BachelorThesisHeroProps> = ({
  selectedPhase,
  kpis,
  onJumpToSection
}) => {
  const currentPhaseMeta = PHASE_METADATA[selectedPhase];
  const [activeNav, setActiveNav] = useState<string | null>(null);

  // Sync active navigation state on scroll
  useEffect(() => {
    const handleScroll = () => {
      const scrollY = window.scrollY;
      if (scrollY < 200) {
        setActiveNav(null);
        return;
      }

      const sec2 = document.getElementById('scalability-trajectories');
      const sec1 = document.getElementById('single-scale-benchmark');

      if (sec2 && scrollY >= sec2.offsetTop - 300) {
        setActiveNav('scalability-trajectories');
      } else if (sec1 && scrollY >= sec1.offsetTop - 300) {
        setActiveNav('single-scale-benchmark');
      }
    };

    window.addEventListener('scroll', handleScroll, { passive: true });
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  const handleScrollTo = (sectionId: string) => {
    setActiveNav(sectionId);
    if (onJumpToSection) {
      onJumpToSection(sectionId);
      return;
    }
    const element = document.getElementById(sectionId);
    if (element) {
      element.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  };

  return (
    <section className="relative w-full min-h-[calc(100vh-7.5rem)] md:min-h-[calc(100vh-8.5rem)] flex flex-col justify-between pt-6 sm:pt-8 md:pt-12 pb-6">
      {/* 1. Main Grid: Left Narrative + Right Stacked KPI Cards */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 lg:gap-12 w-full items-center my-auto">
        {/* Left Column: Thesis Title & Narrative */}
        <div className="lg:col-span-6 flex flex-col items-start justify-center">
          <div className="relative inline-block mb-3">
            <h1 className="font-megrim text-4xl sm:text-5xl lg:text-6xl text-white tracking-wider leading-[1.15]">
              Router Models Benchmark Suite
            </h1>
            <div className="brand-underline mt-2.5" />
          </div>

          <p className="text-slate-200 text-base sm:text-lg leading-relaxed mt-4 font-sans">
            <strong style={{ color: 'var(--brand-light)' }} className="font-semibold">
              Empirical comparative evaluation
            </strong>{' '}
            of semantic routing architectures under extreme tool scaling for local AI copilots.
          </p>

          <p className="text-slate-400 text-sm sm:text-base leading-relaxed mt-3 font-sans">
            Comparing Monolithic Baseline LLMs, 2-Layer Semantic Hybrids (FastEmbed dense embeddings + FAISS Top-K clustering), and LAYA Typed Decision Routers across latency, token burn, and dispatch accuracy.
          </p>
        </div>

        {/* Right Column: 3 Stacked KPI Cards */}
        {kpis && (
          <div className="lg:col-span-6 flex flex-col gap-3.5 sm:gap-4 w-full">
            {/* Card 1: Top Accuracy */}
            <div className="group relative theme-card rounded-2xl p-4 sm:p-5 hover:-translate-y-0.5 transition-all duration-300">
              <div className="flex items-start gap-4">
                <div className="p-3 rounded-xl transition-all duration-300 flex-shrink-0 group-hover:scale-105 theme-icon-box">
                  <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-baseline justify-between gap-2">
                    <h4 className="text-white font-semibold text-base transition-colors group-hover:text-[var(--brand-light)] truncate">
                      Accuracy Leader
                    </h4>
                    <div className="text-xl sm:text-2xl font-extrabold font-mono text-emerald-400 flex items-baseline">
                      {kpis.bestAccuracy.accuracy}
                      <span className="text-sm ml-0.5 font-bold">%</span>
                    </div>
                  </div>
                  <p className="text-xs font-medium text-slate-300 mt-0.5 truncate">
                    {kpis.bestAccuracy.modelName}
                  </p>
                  <p className="text-slate-400 text-xs mt-1 leading-relaxed">
                    {kpis.bestAccuracy.correctCount} of {kpis.bestAccuracy.totalCount} tests passed with verified routing decisions.
                  </p>
                </div>
              </div>
            </div>

            {/* Card 2: Lowest Latency */}
            <div className="group relative theme-card rounded-2xl p-4 sm:p-5 hover:-translate-y-0.5 transition-all duration-300">
              <div className="flex items-start gap-4">
                <div className="p-3 rounded-xl transition-all duration-300 flex-shrink-0 group-hover:scale-105 theme-icon-box">
                  <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M13 10V3L4 14h7v7l9-11h-7z" />
                  </svg>
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-baseline justify-between gap-2">
                    <h4 className="text-white font-semibold text-base transition-colors group-hover:text-[var(--brand-light)] truncate">
                      Latency Frontier
                    </h4>
                    <div className="text-xl sm:text-2xl font-extrabold font-mono text-cyan-400 flex items-baseline">
                      {Math.round(kpis.lowestMeanModel.meanLatencyMs)}
                      <span className="text-sm ml-0.5 font-bold">ms</span>
                    </div>
                  </div>
                  <p className="text-xs font-medium text-slate-300 mt-0.5 truncate">
                    {kpis.lowestMeanModel.modelName}
                  </p>
                  <p className="text-slate-400 text-xs mt-1 leading-relaxed">
                    Median (P50) dispatch time: {Math.round(kpis.lowestMeanModel.p50LatencyMs)}ms under continuous load.
                  </p>
                </div>
              </div>
            </div>

            {/* Card 3: Zero-Token Efficiency */}
            <div className="group relative theme-card rounded-2xl p-4 sm:p-5 hover:-translate-y-0.5 transition-all duration-300">
              <div className="flex items-start gap-4">
                <div className="p-3 rounded-xl transition-all duration-300 flex-shrink-0 group-hover:scale-105 theme-icon-box">
                  <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-baseline justify-between gap-2">
                    <h4 className="text-white font-semibold text-base transition-colors group-hover:text-[var(--brand-light)] truncate">
                      Zero-Token Evaluators
                    </h4>
                    <div className="text-xl sm:text-2xl font-extrabold font-mono text-purple-400 flex items-baseline">
                      {kpis.zeroTokenRouters}
                      <span className="text-sm ml-1 font-bold">Models</span>
                    </div>
                  </div>
                  <p className="text-xs font-medium text-slate-300 mt-0.5 truncate">
                    Deterministic LAYA Routers
                  </p>
                  <p className="text-slate-400 text-xs mt-1 leading-relaxed">
                    0 LLM tokens consumed. Pure typed decision AST execution for zero API costs.
                  </p>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* 2. Quick Jump Navigation & Evaluation Scope */}
      <div className="relative z-10 flex flex-wrap items-center justify-between gap-4 pt-4 pb-4 border-y border-white/[0.08] mt-10 lg:mt-16">
        {/* Independent Standalone Navigation Buttons */}
        <div className="flex flex-wrap items-center gap-3 sm:gap-4">
          <span className="text-xs font-mono uppercase tracking-widest text-slate-400 font-semibold mr-1">
            Quick Navigation:
          </span>

          {/* Button 1: Single-Scale Benchmark */}
          <button
            type="button"
            onClick={() => handleScrollTo('single-scale-benchmark')}
            className={`group relative px-4 py-2 sm:px-5 sm:py-2.5 rounded-xl text-xs sm:text-sm font-mono tracking-wider transition-all duration-300 cursor-pointer flex items-center gap-2.5 border backdrop-blur-md ${
              activeNav === 'single-scale-benchmark'
                ? 'bg-white text-zinc-950 font-bold border-white shadow-[0_6px_22px_rgba(255,255,255,0.28)] -translate-y-1 scale-[1.03]'
                : 'bg-white/[0.04] text-slate-300 border-white/[0.12] hover:bg-white/[0.09] hover:text-white hover:border-white/35 hover:-translate-y-1 hover:shadow-[0_10px_24px_rgba(0,0,0,0.5)] hover:scale-[1.02] active:scale-[0.98]'
            }`}
          >
            <svg
              className={`w-4 h-4 transition-transform duration-300 group-hover:scale-110 ${
                activeNav === 'single-scale-benchmark'
                  ? 'text-zinc-950'
                  : 'text-[var(--brand-primary)]'
              }`}
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2.2}
                d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"
              />
            </svg>
            <span>Single-Scale Benchmark</span>
          </button>

          {/* Button 2: Scalability Trajectories */}
          <button
            type="button"
            onClick={() => handleScrollTo('scalability-trajectories')}
            className={`group relative px-4 py-2 sm:px-5 sm:py-2.5 rounded-xl text-xs sm:text-sm font-mono tracking-wider transition-all duration-300 cursor-pointer flex items-center gap-2.5 border backdrop-blur-md ${
              activeNav === 'scalability-trajectories'
                ? 'bg-white text-zinc-950 font-bold border-white shadow-[0_6px_22px_rgba(255,255,255,0.28)] -translate-y-1 scale-[1.03]'
                : 'bg-white/[0.04] text-slate-300 border-white/[0.12] hover:bg-white/[0.09] hover:text-white hover:border-white/35 hover:-translate-y-1 hover:shadow-[0_10px_24px_rgba(0,0,0,0.5)] hover:scale-[1.02] active:scale-[0.98]'
            }`}
          >
            <svg
              className={`w-4 h-4 transition-transform duration-300 group-hover:scale-110 ${
                activeNav === 'scalability-trajectories'
                  ? 'text-zinc-950'
                  : 'text-[var(--brand-primary)]'
              }`}
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2.2}
                d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6"
              />
            </svg>
            <span>Scalability Trajectories (20 → 100 Tools)</span>
          </button>
        </div>

        {/* Current Active Filter Indicator */}
        <div className="flex items-center gap-2 text-xs font-mono text-slate-400">
          <span className="w-1.5 h-1.5 rounded-full" style={{ backgroundColor: currentPhaseMeta.color }} />
          <span>Active Phase:</span>
          <span className="text-white font-medium">{currentPhaseMeta.label}</span>
        </div>
      </div>
    </section>
  );
};

export default BachelorThesisHero;
