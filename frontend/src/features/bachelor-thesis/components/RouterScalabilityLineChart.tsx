import React, { useState } from 'react';
import type { ModelTrajectory } from '../data/routerBenchmarkData';

export interface RouterScalabilityLineChartProps {
  trajectories: ModelTrajectory[];
  phase: string;
  latencyMetric?: 'mean' | 'p50';
  isDarkMode?: boolean;
}

interface HoverState {
  modelId: string;
  numTools: number;
  accuracy: number;
  meanLatency: number;
  p50Latency: number;
  tokensPerCall: number;
  totalTokens: number;
  xPos: number;
  yPos: number;
}

/**
 * RouterScalabilityLineChart Component
 *
 * Implements a publication-ready 4-panel line chart tracking router trajectory across
 * tool scaling tiers (20, 30, 50, and 100 tools):
 * Panel 1: Routing Accuracy (%)
 * Panel 2: Routing Latency (ms) [P50 & Mean when single model; multi-model lines when comparing]
 * Panel 3: Avg Tokens Per LLM Call (Context Complexity)
 * Panel 4: Total Cumulative Tokens (Cumulative Benchmark Cost)
 */
export const RouterScalabilityLineChart: React.FC<RouterScalabilityLineChartProps> = ({
  trajectories,
  phase,
  latencyMetric = 'mean',
  isDarkMode = false
}) => {
  const [hoveredState, setHoveredState] = useState<HoverState | null>(null);
  const [focusedModelId, setFocusedModelId] = useState<string | null>(null);

  if (!trajectories || trajectories.length === 0) {
    return (
      <div className={`w-full py-20 px-4 text-center rounded-2xl border ${
        isDarkMode 
          ? 'bg-black/40 border-white/10 text-slate-400' 
          : 'bg-white border-slate-200 text-slate-500 shadow-sm'
      }`}>
        <p className="text-base font-medium">No models selected for trajectory comparison.</p>
        <p className="text-xs mt-1 text-slate-400">Enable at least one model from the filter below to view scalability curves.</p>
      </div>
    );
  }

  const isSingleModel = trajectories.length === 1;
  const singleModel = isSingleModel ? trajectories[0] : null;

  // Layout coordinate constants
  const viewBoxWidth = 1340;
  const headerHeight = isSingleModel ? 68 : 96;
  const footerHeight = 45;
  const plotHeight = 260;
  const totalSvgHeight = headerHeight + plotHeight + footerHeight;

  const leftMargin = 55;
  const rightMargin = 25;
  const colGap = 24;
  const usableWidth = viewBoxWidth - leftMargin - rightMargin - (colGap * 3);
  const panelWidth = Math.floor(usableWidth / 4); // ~285px each

  const panelX = [
    leftMargin,
    leftMargin + panelWidth + colGap,
    leftMargin + (panelWidth + colGap) * 2,
    leftMargin + (panelWidth + colGap) * 3,
  ];

  // X-scale coordinate mapper (linear spacing across 20 -> 100 tools with padding)
  const xPadding = 26;
  const innerPlotWidth = panelWidth - (xPadding * 2);

  const getX = (tools: number): number => {
    const norm = (tools - 20) / (100 - 20); // 0.0 at 20, 0.125 at 30, 0.375 at 50, 1.0 at 100
    return xPadding + norm * innerPlotWidth;
  };

  const toolTicks = [20, 30, 50, 100];

  // Theme styling colors
  const bgFill = isDarkMode ? '#0a0d14' : '#ffffff';
  const panelBorder = isDarkMode ? '#1e293b' : '#334155';
  const gridLineColor = isDarkMode ? 'rgba(255, 255, 255, 0.08)' : 'rgba(0, 0, 0, 0.08)';
  const textColor = isDarkMode ? '#f8fafc' : '#0f172a';
  const subtextColor = isDarkMode ? '#94a3b8' : '#475569';

  // Y-axis scaling for Panel 2 (Latency)
  const allLatencies = trajectories.flatMap(t => 
    isSingleModel 
      ? t.points.flatMap(p => [p.p50LatencyMs, p.meanLatencyMs])
      : t.points.map(p => latencyMetric === 'mean' ? p.meanLatencyMs : p.p50LatencyMs)
  );
  const rawMaxLat = Math.max(...allLatencies, 100);
  const panel2Max = Math.ceil(rawMaxLat * 1.15 / 200) * 200 || 1500;
  const panel2Min = isSingleModel && Math.min(...allLatencies) > 700 ? Math.floor(Math.min(...allLatencies) * 0.9 / 100) * 100 : 0;

  // Y-axis scaling for Panel 3 (Avg Tokens Per Call)
  const allTokensPerCall = trajectories.flatMap(t => t.points.map(p => p.avgTokensPerCall));
  const rawMaxTPC = Math.max(...allTokensPerCall, 10);
  const panel3Max = Math.ceil(rawMaxTPC * 1.2 / 500) * 500 || 20;

  // Y-axis scaling for Panel 4 (Total Cumulative Tokens)
  const allTotalTokens = trajectories.flatMap(t => t.points.map(p => p.totalTokens));
  const rawMaxTot = Math.max(...allTotalTokens, 100);
  const panel4Max = Math.ceil(rawMaxTot * 1.2 / 10000) * 10000 || 50;

  // Title text
  const figureTitle = isSingleModel
    ? `Scalability Trajectory: ${singleModel?.modelName} (Phase: ${phase})`
    : `Router Scalability Comparison across Tool Scale (Phase: ${phase})`;

  return (
    <div className={`w-full overflow-x-auto rounded-2xl border transition-all duration-300 shadow-xl ${
      isDarkMode 
        ? 'bg-[#06080d]/90 border-white/10' 
        : 'bg-white border-slate-200'
    }`}>
      <div className="min-w-[960px] p-4 md:p-6 select-none relative">
        <svg
          viewBox={`0 0 ${viewBoxWidth} ${totalSvgHeight}`}
          className="w-full h-auto overflow-visible font-sans"
        >
          {/* Main Figure Title */}
          <text
            x={viewBoxWidth / 2}
            y={28}
            textAnchor="middle"
            fill={textColor}
            fontSize="16"
            fontWeight="700"
            letterSpacing="-0.01em"
          >
            {figureTitle}
          </text>

          {/* Multi-model Legend Banner (when comparing 2+ models - centered with ample vertical headroom) */}
          {!isSingleModel && (
            <g transform={`translate(${viewBoxWidth / 2}, 54)`}>
              {(() => {
                const itemSpacing = 180;
                const totalLegendWidth = trajectories.length * itemSpacing;
                const startX = -totalLegendWidth / 2 + 10;
                return trajectories.map((traj, idx) => {
                  const xOffset = startX + idx * itemSpacing;
                  const isHovered = focusedModelId === traj.modelId;
                  return (
                    <g
                      key={`legend-${traj.modelId}`}
                      transform={`translate(${xOffset}, 0)`}
                      className="cursor-pointer transition-opacity duration-150"
                      onMouseEnter={() => setFocusedModelId(traj.modelId)}
                      onMouseLeave={() => setFocusedModelId(null)}
                      opacity={focusedModelId && !isHovered ? 0.35 : 1}
                    >
                      <line x1={0} y1={0} x2={16} y2={0} stroke={traj.color} strokeWidth="2.8" />
                      <circle cx={8} cy={0} r={4} fill={traj.color} />
                      <text x={22} y={3.5} fill={isHovered ? traj.color : textColor} fontSize="11" fontWeight="700">
                        {traj.modelName}
                      </text>
                    </g>
                  );
                });
              })()}
            </g>
          )}

          {/* =========================================================================
              PANEL 1: ROUTING ACCURACY (%)
             ========================================================================= */}
          <g transform={`translate(${panelX[0]}, ${headerHeight})`}>
            {/* Title */}
            <text x={panelWidth / 2} y={-12} textAnchor="middle" fill={textColor} fontSize="12" fontWeight="700">
              Routing Accuracy (%)
            </text>

            {/* Box */}
            <rect x={0} y={0} width={panelWidth} height={plotHeight} fill={bgFill} stroke={panelBorder} strokeWidth="1.2" />

            {/* Horizontal Grid (0, 20, 40, 60, 80, 100) */}
            {[0, 20, 40, 60, 80, 100].map((tick) => {
              const yPos = plotHeight - (tick / 105) * plotHeight;
              return (
                <g key={`p1-grid-${tick}`}>
                  <line x1={0} y1={yPos} x2={panelWidth} y2={yPos} stroke={gridLineColor} strokeDasharray="3 3" strokeWidth="1" />
                  <text x={-6} y={yPos + 3.5} textAnchor="end" fill={subtextColor} fontSize="9" fontWeight="500">
                    {tick}
                  </text>
                </g>
              );
            })}

            {/* Vertical Tool Count Grid */}
            {toolTicks.map((t) => {
              const xPos = getX(t);
              return (
                <g key={`p1-xtick-${t}`}>
                  <line x1={xPos} y1={0} x2={xPos} y2={plotHeight} stroke={gridLineColor} strokeDasharray="3 3" strokeWidth="1" />
                  <text x={xPos} y={plotHeight + 15} textAnchor="middle" fill={subtextColor} fontSize="10" fontWeight="500">
                    {t}
                  </text>
                </g>
              );
            })}

            {/* X-Axis Caption */}
            <text x={panelWidth / 2} y={plotHeight + 32} textAnchor="middle" fill={subtextColor} fontSize="10" fontWeight="600">
              Number of Tools
            </text>
            <text x={-32} y={plotHeight / 2} textAnchor="middle" fill={subtextColor} fontSize="10" fontWeight="600" transform={`rotate(-90, -32, ${plotHeight / 2})`}>
              Accuracy (%)
            </text>

            {/* Plot Lines */}
            {trajectories.map((traj) => {
              const isFocused = !focusedModelId || focusedModelId === traj.modelId;
              const pointsStr = traj.points.map((p) => {
                const x = getX(p.numTools);
                const y = plotHeight - (p.accuracy / 105) * plotHeight;
                return `${x},${y}`;
              }).join(' ');

              return (
                <g
                  key={`p1-traj-${traj.modelId}`}
                  opacity={isFocused ? 1 : 0.25}
                  className="transition-opacity duration-200"
                >
                  <polyline
                    fill="none"
                    stroke={traj.color}
                    strokeWidth="2.4"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    points={pointsStr}
                  />
                  {traj.points.map((p) => {
                    const x = getX(p.numTools);
                    const y = plotHeight - (p.accuracy / 105) * plotHeight;
                    return (
                      <g
                        key={`p1-pt-${traj.modelId}-${p.numTools}`}
                        className="cursor-pointer"
                        onMouseEnter={() => setHoveredState({
                          modelId: traj.modelId,
                          numTools: p.numTools,
                          accuracy: p.accuracy,
                          meanLatency: p.meanLatencyMs,
                          p50Latency: p.p50LatencyMs,
                          tokensPerCall: p.avgTokensPerCall,
                          totalTokens: p.totalTokens,
                          xPos: panelX[0] + x,
                          yPos: headerHeight + y
                        })}
                        onMouseLeave={() => setHoveredState(null)}
                      >
                        <circle cx={x} cy={y} r={isFocused ? 4.5 : 3.5} fill={traj.color} stroke={bgFill} strokeWidth="1.5" />
                        {/* Display value label if single model or focused */}
                        {(isSingleModel || focusedModelId === traj.modelId) && (
                          <text x={x} y={y - 8} textAnchor="middle" fill={textColor} fontSize="8.5" fontWeight="700">
                            {p.accuracy.toFixed(1)}%
                          </text>
                        )}
                      </g>
                    );
                  })}
                </g>
              );
            })}
          </g>

          {/* =========================================================================
              PANEL 2: ROUTING LATENCY (ms)
             ========================================================================= */}
          <g transform={`translate(${panelX[1]}, ${headerHeight})`}>
            {/* Title */}
            <text x={panelWidth / 2} y={-12} textAnchor="middle" fill={textColor} fontSize="12" fontWeight="700">
              Routing Latency (ms)
            </text>

            {/* Box */}
            <rect x={0} y={0} width={panelWidth} height={plotHeight} fill={bgFill} stroke={panelBorder} strokeWidth="1.2" />

            {/* Y-Grid Ticks for Latency */}
            {(() => {
              const range = panel2Max - panel2Min;
              const step = range <= 600 ? 100 : range <= 1500 ? 250 : 500;
              const ticks = [];
              for (let t = panel2Min; t <= panel2Max; t += step) {
                ticks.push(t);
              }
              return ticks.map((tick) => {
                const yPos = plotHeight - ((tick - panel2Min) / (panel2Max - panel2Min)) * plotHeight;
                return (
                  <g key={`p2-grid-${tick}`}>
                    <line x1={0} y1={yPos} x2={panelWidth} y2={yPos} stroke={gridLineColor} strokeDasharray="3 3" strokeWidth="1" />
                    <text x={-6} y={yPos + 3.5} textAnchor="end" fill={subtextColor} fontSize="8.5" fontWeight="500">
                      {tick}
                    </text>
                  </g>
                );
              });
            })()}

            {/* Vertical Tool Count Grid */}
            {toolTicks.map((t) => {
              const xPos = getX(t);
              return (
                <g key={`p2-xtick-${t}`}>
                  <line x1={xPos} y1={0} x2={xPos} y2={plotHeight} stroke={gridLineColor} strokeDasharray="3 3" strokeWidth="1" />
                  <text x={xPos} y={plotHeight + 15} textAnchor="middle" fill={subtextColor} fontSize="10" fontWeight="500">
                    {t}
                  </text>
                </g>
              );
            })}

            {/* Captions */}
            <text x={panelWidth / 2} y={plotHeight + 32} textAnchor="middle" fill={subtextColor} fontSize="10" fontWeight="600">
              Number of Tools
            </text>
            <text x={-35} y={plotHeight / 2} textAnchor="middle" fill={subtextColor} fontSize="10" fontWeight="600" transform={`rotate(-90, -35, ${plotHeight / 2})`}>
              Latency (ms)
            </text>

            {/* If Single Model: Replicate exact matplotlib dual-curve (P50 & Mean) */}
            {isSingleModel && singleModel && (
              <>
                {/* P50 Line (Solid Green #059669 with squares) */}
                {(() => {
                  const ptsP50 = singleModel.points.map(p => {
                    const x = getX(p.numTools);
                    const y = plotHeight - ((p.p50LatencyMs - panel2Min) / (panel2Max - panel2Min)) * plotHeight;
                    return `${x},${y}`;
                  }).join(' ');

                  return (
                    <g>
                      <polyline fill="none" stroke="#059669" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" points={ptsP50} />
                      {singleModel.points.map(p => {
                        const x = getX(p.numTools);
                        const y = plotHeight - ((p.p50LatencyMs - panel2Min) / (panel2Max - panel2Min)) * plotHeight;
                        return (
                          <g key={`p50-pt-${p.numTools}`}>
                            <rect x={x - 4} y={y - 4} width={8} height={8} fill="#059669" stroke={bgFill} strokeWidth="1" />
                            <text x={x} y={y - 8} textAnchor="middle" fill={textColor} fontSize="8" fontWeight="600">
                              {Math.round(p.p50LatencyMs)}ms
                            </text>
                          </g>
                        );
                      })}
                    </g>
                  );
                })()}

                {/* Mean Line (Dashed Emerald #34D399 with triangles) */}
                {(() => {
                  const ptsMean = singleModel.points.map(p => {
                    const x = getX(p.numTools);
                    const y = plotHeight - ((p.meanLatencyMs - panel2Min) / (panel2Max - panel2Min)) * plotHeight;
                    return `${x},${y}`;
                  }).join(' ');

                  return (
                    <g>
                      <polyline fill="none" stroke="#34D399" strokeWidth="2.0" strokeDasharray="5 3" strokeLinecap="round" strokeLinejoin="round" points={ptsMean} />
                      {singleModel.points.map(p => {
                        const x = getX(p.numTools);
                        const y = plotHeight - ((p.meanLatencyMs - panel2Min) / (panel2Max - panel2Min)) * plotHeight;
                        return (
                          <g key={`mean-pt-${p.numTools}`}>
                            <polygon points={`${x},${y - 5} ${x - 4.5},${y + 4} ${x + 4.5},${y + 4}`} fill="#34D399" stroke={bgFill} strokeWidth="1" />
                            <text x={x + 4} y={y + 13} textAnchor="start" fill={subtextColor} fontSize="7.5" fontWeight="600">
                              {Math.round(p.meanLatencyMs)}ms
                            </text>
                          </g>
                        );
                      })}
                    </g>
                  );
                })()}

                {/* Single Model Latency Legend at Top-Left */}
                <g transform="translate(8, 8)">
                  <rect x={0} y={0} width={92} height={34} fill={isDarkMode ? 'rgba(15, 23, 42, 0.92)' : 'rgba(255, 255, 255, 0.95)'} stroke={panelBorder} strokeWidth="0.8" rx={4} />
                  <rect x={6} y={7} width={8} height={8} fill="#059669" />
                  <text x={18} y={14} fill={textColor} fontSize="8" fontWeight="600">P50 (Median)</text>
                  <polygon points="10,21 6,28 14,28" fill="#34D399" />
                  <text x={18} y={26} fill={textColor} fontSize="8" fontWeight="600">Mean</text>
                </g>
              </>
            )}

            {/* If Multi-Model Comparison: Plot each active model's line */}
            {!isSingleModel && trajectories.map((traj) => {
              const isFocused = !focusedModelId || focusedModelId === traj.modelId;
              const pointsStr = traj.points.map(p => {
                const val = latencyMetric === 'mean' ? p.meanLatencyMs : p.p50LatencyMs;
                const x = getX(p.numTools);
                const y = plotHeight - ((val - panel2Min) / (panel2Max - panel2Min)) * plotHeight;
                return `${x},${y}`;
              }).join(' ');

              return (
                <g
                  key={`p2-traj-${traj.modelId}`}
                  opacity={isFocused ? 1 : 0.25}
                  className="transition-opacity duration-200"
                >
                  <polyline
                    fill="none"
                    stroke={traj.color}
                    strokeWidth="2.4"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    points={pointsStr}
                  />
                  {traj.points.map(p => {
                    const val = latencyMetric === 'mean' ? p.meanLatencyMs : p.p50LatencyMs;
                    const x = getX(p.numTools);
                    const y = plotHeight - ((val - panel2Min) / (panel2Max - panel2Min)) * plotHeight;
                    return (
                      <g
                        key={`p2-pt-${traj.modelId}-${p.numTools}`}
                        className="cursor-pointer"
                        onMouseEnter={() => setHoveredState({
                          modelId: traj.modelId,
                          numTools: p.numTools,
                          accuracy: p.accuracy,
                          meanLatency: p.meanLatencyMs,
                          p50Latency: p.p50LatencyMs,
                          tokensPerCall: p.avgTokensPerCall,
                          totalTokens: p.totalTokens,
                          xPos: panelX[1] + x,
                          yPos: headerHeight + y
                        })}
                        onMouseLeave={() => setHoveredState(null)}
                      >
                        <circle cx={x} cy={y} r={isFocused ? 4.5 : 3.5} fill={traj.color} stroke={bgFill} strokeWidth="1.5" />
                        {focusedModelId === traj.modelId && (
                          <text x={x} y={y - 8} textAnchor="middle" fill={textColor} fontSize="8" fontWeight="700">
                            {Math.round(val)}ms
                          </text>
                        )}
                      </g>
                    );
                  })}
                </g>
              );
            })}
          </g>

          {/* =========================================================================
              PANEL 3: AVG TOKENS PER LLM CALL
             ========================================================================= */}
          <g transform={`translate(${panelX[2]}, ${headerHeight})`}>
            {/* Title */}
            <text x={panelWidth / 2} y={-12} textAnchor="middle" fill={textColor} fontSize="12" fontWeight="700">
              Avg Tokens Per LLM Call
            </text>

            {/* Box */}
            <rect x={0} y={0} width={panelWidth} height={plotHeight} fill={bgFill} stroke={panelBorder} strokeWidth="1.2" />

            {/* Y-Grid Ticks for Tokens Per Call */}
            {(() => {
              const step = panel3Max <= 50 ? 10 : panel3Max <= 2000 ? 500 : 1000;
              const ticks = [];
              for (let t = 0; t <= panel3Max; t += step) {
                ticks.push(t);
              }
              return ticks.map((tick) => {
                const yPos = plotHeight - (tick / panel3Max) * plotHeight;
                return (
                  <g key={`p3-grid-${tick}`}>
                    <line x1={0} y1={yPos} x2={panelWidth} y2={yPos} stroke={gridLineColor} strokeDasharray="3 3" strokeWidth="1" />
                    <text x={-6} y={yPos + 3.5} textAnchor="end" fill={subtextColor} fontSize="8.5" fontWeight="500">
                      {tick}
                    </text>
                  </g>
                );
              });
            })()}

            {/* Vertical Tool Count Grid */}
            {toolTicks.map((t) => {
              const xPos = getX(t);
              return (
                <g key={`p3-xtick-${t}`}>
                  <line x1={xPos} y1={0} x2={xPos} y2={plotHeight} stroke={gridLineColor} strokeDasharray="3 3" strokeWidth="1" />
                  <text x={xPos} y={plotHeight + 15} textAnchor="middle" fill={subtextColor} fontSize="10" fontWeight="500">
                    {t}
                  </text>
                </g>
              );
            })}

            {/* Captions */}
            <text x={panelWidth / 2} y={plotHeight + 32} textAnchor="middle" fill={subtextColor} fontSize="10" fontWeight="600">
              Number of Tools
            </text>
            <text x={-35} y={plotHeight / 2} textAnchor="middle" fill={subtextColor} fontSize="10" fontWeight="600" transform={`rotate(-90, -35, ${plotHeight / 2})`}>
              Tokens per Invocation
            </text>

            {/* Plot Lines */}
            {trajectories.map((traj) => {
              const isFocused = !focusedModelId || focusedModelId === traj.modelId;
              const pointsStr = traj.points.map(p => {
                const x = getX(p.numTools);
                const y = plotHeight - (p.avgTokensPerCall / panel3Max) * plotHeight;
                return `${x},${y}`;
              }).join(' ');

              return (
                <g
                  key={`p3-traj-${traj.modelId}`}
                  opacity={isFocused ? 1 : 0.25}
                  className="transition-opacity duration-200"
                >
                  <polyline
                    fill="none"
                    stroke={traj.color}
                    strokeWidth="2.4"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    points={pointsStr}
                  />
                  {traj.points.map(p => {
                    const x = getX(p.numTools);
                    const y = plotHeight - (p.avgTokensPerCall / panel3Max) * plotHeight;
                    const labelTxt = traj.isLaya || p.avgTokensPerCall === 0 ? '0 (LAYA)' : `${Math.round(p.avgTokensPerCall)}`;

                    return (
                      <g
                        key={`p3-pt-${traj.modelId}-${p.numTools}`}
                        className="cursor-pointer"
                        onMouseEnter={() => setHoveredState({
                          modelId: traj.modelId,
                          numTools: p.numTools,
                          accuracy: p.accuracy,
                          meanLatency: p.meanLatencyMs,
                          p50Latency: p.p50LatencyMs,
                          tokensPerCall: p.avgTokensPerCall,
                          totalTokens: p.totalTokens,
                          xPos: panelX[2] + x,
                          yPos: headerHeight + y
                        })}
                        onMouseLeave={() => setHoveredState(null)}
                      >
                        {/* Diamond marker */}
                        <polygon
                          points={`${x},${y - 4} ${x + 4},${y} ${x},${y + 4} ${x - 4},${y}`}
                          fill={traj.color}
                          stroke={bgFill}
                          strokeWidth="1.2"
                        />
                        {(isSingleModel || focusedModelId === traj.modelId) && (
                          <text x={x} y={y - 8} textAnchor="middle" fill={textColor} fontSize="7.5" fontWeight="700">
                            {labelTxt}
                          </text>
                        )}
                      </g>
                    );
                  })}
                </g>
              );
            })}
          </g>

          {/* =========================================================================
              PANEL 4: TOTAL CUMULATIVE TOKENS
             ========================================================================= */}
          <g transform={`translate(${panelX[3]}, ${headerHeight})`}>
            {/* Title */}
            <text x={panelWidth / 2} y={-12} textAnchor="middle" fill={textColor} fontSize="12" fontWeight="700">
              Total Cumulative Tokens
            </text>

            {/* Box */}
            <rect x={0} y={0} width={panelWidth} height={plotHeight} fill={bgFill} stroke={panelBorder} strokeWidth="1.2" />

            {/* Y-Grid Ticks for Cumulative Tokens (dynamically stepped for 4-6 clean ticks) */}
            {(() => {
              let step = 20;
              if (panel4Max > 100 && panel4Max <= 2000) step = 500;
              else if (panel4Max > 2000 && panel4Max <= 20000) step = 5000;
              else if (panel4Max > 20000 && panel4Max <= 100000) step = 25000;
              else if (panel4Max > 100000 && panel4Max <= 500000) step = 100000;
              else if (panel4Max > 500000 && panel4Max <= 1000000) step = 250000;
              else if (panel4Max > 1000000) step = 500000;

              const ticks = [];
              for (let t = 0; t <= panel4Max; t += step) {
                ticks.push(t);
              }
              return ticks.map((tick) => {
                const yPos = plotHeight - (tick / panel4Max) * plotHeight;
                return (
                  <g key={`p4-grid-${tick}`}>
                    <line x1={0} y1={yPos} x2={panelWidth} y2={yPos} stroke={gridLineColor} strokeDasharray="3 3" strokeWidth="1" />
                    <text x={-6} y={yPos + 3.5} textAnchor="end" fill={subtextColor} fontSize="8.5" fontWeight="500">
                      {tick >= 1000000 ? `${(tick / 1000000).toFixed(1)}M` : tick >= 1000 ? `${Math.round(tick / 1000)}k` : tick}
                    </text>
                  </g>
                );
              });
            })()}

            {/* Vertical Tool Count Grid */}
            {toolTicks.map((t) => {
              const xPos = getX(t);
              return (
                <g key={`p4-xtick-${t}`}>
                  <line x1={xPos} y1={0} x2={xPos} y2={plotHeight} stroke={gridLineColor} strokeDasharray="3 3" strokeWidth="1" />
                  <text x={xPos} y={plotHeight + 15} textAnchor="middle" fill={subtextColor} fontSize="10" fontWeight="500">
                    {t}
                  </text>
                </g>
              );
            })}

            {/* Captions */}
            <text x={panelWidth / 2} y={plotHeight + 32} textAnchor="middle" fill={subtextColor} fontSize="10" fontWeight="600">
              Number of Tools
            </text>
            <text x={-35} y={plotHeight / 2} textAnchor="middle" fill={subtextColor} fontSize="10" fontWeight="600" transform={`rotate(-90, -35, ${plotHeight / 2})`}>
              Total Tokens
            </text>

            {/* Plot Lines */}
            {trajectories.map((traj) => {
              const isFocused = !focusedModelId || focusedModelId === traj.modelId;
              const pointsStr = traj.points.map(p => {
                const x = getX(p.numTools);
                const y = plotHeight - (p.totalTokens / panel4Max) * plotHeight;
                return `${x},${y}`;
              }).join(' ');

              return (
                <g
                  key={`p4-traj-${traj.modelId}`}
                  opacity={isFocused ? 1 : 0.25}
                  className="transition-opacity duration-200"
                >
                  <polyline
                    fill="none"
                    stroke={traj.color}
                    strokeWidth="2.4"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    points={pointsStr}
                  />
                  {traj.points.map(p => {
                    const x = getX(p.numTools);
                    const y = plotHeight - (p.totalTokens / panel4Max) * plotHeight;
                    const labelTxt = traj.isLaya || p.totalTokens === 0 ? '0 (LAYA)' : `${p.totalTokens.toLocaleString()}`;

                    return (
                      <g
                        key={`p4-pt-${traj.modelId}-${p.numTools}`}
                        className="cursor-pointer"
                        onMouseEnter={() => setHoveredState({
                          modelId: traj.modelId,
                          numTools: p.numTools,
                          accuracy: p.accuracy,
                          meanLatency: p.meanLatencyMs,
                          p50Latency: p.p50LatencyMs,
                          tokensPerCall: p.avgTokensPerCall,
                          totalTokens: p.totalTokens,
                          xPos: panelX[3] + x,
                          yPos: headerHeight + y
                        })}
                        onMouseLeave={() => setHoveredState(null)}
                      >
                        {/* Cross/Square Marker */}
                        <rect
                          x={x - 3.5}
                          y={y - 3.5}
                          width={7}
                          height={7}
                          fill={traj.color}
                          stroke={bgFill}
                          strokeWidth="1.2"
                        />
                        {(isSingleModel || focusedModelId === traj.modelId) && (
                          <text x={x} y={y - 8} textAnchor="middle" fill={textColor} fontSize="7.5" fontWeight="700">
                            {labelTxt}
                          </text>
                        )}
                      </g>
                    );
                  })}
                </g>
              );
            })}
          </g>
        </svg>

        {/* Floating Tooltip for Interactive Inspection */}
        {hoveredState && (
          <div
            className="absolute z-30 pointer-events-none rounded-xl p-3 shadow-2xl border text-xs flex flex-col gap-1 transition-all duration-150 backdrop-blur-xl"
            style={{
              left: `${Math.min(hoveredState.xPos + 15, viewBoxWidth - 220)}px`,
              top: `${hoveredState.yPos - 20}px`,
              backgroundColor: isDarkMode ? 'rgba(10, 14, 23, 0.96)' : 'rgba(255, 255, 255, 0.98)',
              borderColor: isDarkMode ? 'rgba(255, 255, 255, 0.15)' : 'rgba(0, 0, 0, 0.15)',
              color: isDarkMode ? '#f8fafc' : '#0f172a'
            }}
          >
            <div className="font-bold flex items-center justify-between gap-3 border-b pb-1 border-white/10">
              <span>{hoveredState.modelId}</span>
              <span className="font-mono text-cyan-400">{hoveredState.numTools} Tools</span>
            </div>
            <div className="grid grid-cols-2 gap-x-3 gap-y-0.5 text-[11px] pt-0.5 font-mono">
              <span className="text-slate-400">Accuracy:</span>
              <span className="font-bold text-emerald-400 text-right">{hoveredState.accuracy}%</span>
              <span className="text-slate-400">Mean Latency:</span>
              <span className="font-bold text-right">{Math.round(hoveredState.meanLatency)}ms</span>
              <span className="text-slate-400">P50 Latency:</span>
              <span className="font-bold text-right">{Math.round(hoveredState.p50Latency)}ms</span>
              <span className="text-slate-400">Tokens/Call:</span>
              <span className="font-bold text-right">{hoveredState.tokensPerCall > 0 ? Math.round(hoveredState.tokensPerCall) : '0 (LAYA)'}</span>
              <span className="text-slate-400">Total Tokens:</span>
              <span className="font-bold text-purple-400 text-right">{hoveredState.totalTokens.toLocaleString()}</span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default RouterScalabilityLineChart;

