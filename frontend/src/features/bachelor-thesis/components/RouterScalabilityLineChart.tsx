import React, { useState } from 'react';
import type { ModelTrajectory } from '../data/routerBenchmarkData';

export interface RouterScalabilityLineChartProps {
  trajectories: ModelTrajectory[];
  phase: string;
  latencyMetric?: 'mean' | 'p50';
  isDarkMode?: boolean;
  comparisonMode?: 'models' | 'phases';
  comparedModelId?: string;
  comparedModelName?: string;
}

interface HoverState {
  seriesId: string;
  seriesName: string;
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
 * Panel 2: Routing Latency (ms) [P50 & Mean when single model; multi-curve when comparing models or phases]
 * Panel 3: Avg Tokens Per LLM Call (Context Complexity)
 * Panel 4: Total Cumulative Tokens (Cumulative Benchmark Cost)
 *
 * Supports two analysis modes:
 * - 'models': Compare multiple router models within a chosen phase.
 * - 'phases': Compare a single chosen model across all 3 phases (Phase 1 vs 2 vs 3).
 */
export const RouterScalabilityLineChart: React.FC<RouterScalabilityLineChartProps> = ({
  trajectories,
  phase,
  latencyMetric = 'mean',
  isDarkMode = false,
  comparisonMode = 'models',
  comparedModelName
}) => {
  const [hoveredState, setHoveredState] = useState<HoverState | null>(null);
  const [focusedModelId, setFocusedModelId] = useState<string | null>(null);

  const isPhaseMode = comparisonMode === 'phases';

  const isSingleModel = !isPhaseMode && trajectories && trajectories.length === 1;
  const singleModel = isSingleModel ? trajectories[0] : null;

  // Layout coordinate constants - strictly fixed height to prevent vertical layout shifts
  const viewBoxWidth = 1340;
  const headerHeight = 96;
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
  const allLatencies = trajectories && trajectories.length > 0
    ? trajectories.flatMap(t =>
      isSingleModel
        ? t.points.flatMap(p => [p.p50LatencyMs, p.meanLatencyMs])
        : t.points.map(p => latencyMetric === 'mean' ? p.meanLatencyMs : p.p50LatencyMs)
    )
    : [];
  const rawMaxLat = allLatencies.length > 0 ? Math.max(...allLatencies, 100) : 1000;
  const panel2Max = Math.ceil(rawMaxLat * 1.15 / 200) * 200 || 1500;
  const panel2Min = isSingleModel && allLatencies.length > 0 && Math.min(...allLatencies) > 700
    ? Math.floor(Math.min(...allLatencies) * 0.9 / 100) * 100
    : 0;

  // Y-axis scaling for Panel 3 (Avg Tokens Per Call)
  const allTokensPerCall = trajectories && trajectories.length > 0
    ? trajectories.flatMap(t => t.points.map(p => p.avgTokensPerCall))
    : [];
  const rawMaxTPC = allTokensPerCall.length > 0 ? Math.max(...allTokensPerCall, 10) : 500;
  const panel3Max = Math.ceil(rawMaxTPC * 1.2 / 500) * 500 || 20;

  // Y-axis scaling for Panel 4 (Total Cumulative Tokens)
  const allTotalTokens = trajectories && trajectories.length > 0
    ? trajectories.flatMap(t => t.points.map(p => p.totalTokens))
    : [];
  const rawMaxTot = allTotalTokens.length > 0 ? Math.max(...allTotalTokens, 100) : 10000;
  const panel4Max = Math.ceil(rawMaxTot * 1.2 / 10000) * 10000 || 50;

  // Main Figure Title
  const figureTitle = isPhaseMode
    ? `Cross-Phase Scalability: ${comparedModelName || 'Model'} (Phase 1 vs Phase 2 vs Phase 3)`
    : isSingleModel
      ? `Scalability Trajectory: ${singleModel?.modelName} (Phase: ${phase})`
      : `Router Scalability Comparison across Tool Scale (Phase: ${phase})`;

  // Helper to render distinct geometric markers for phases or models
  const renderPointMarker = (
    trajId: string,
    x: number,
    y: number,
    color: string,
    isFocused: boolean
  ) => {
    if (isPhaseMode) {
      if (trajId === 'phase1') {
        return (
          <circle
            cx={x}
            cy={y}
            r={isFocused ? 5.2 : 4.2}
            fill={color}
            stroke={bgFill}
            strokeWidth="1.5"
          />
        );
      }
      if (trajId === 'phase2') {
        return (
          <rect
            x={x - (isFocused ? 4.5 : 3.8)}
            y={y - (isFocused ? 4.5 : 3.8)}
            width={isFocused ? 9 : 7.6}
            height={isFocused ? 9 : 7.6}
            fill={color}
            stroke={bgFill}
            strokeWidth="1.5"
          />
        );
      }
      // phase3 -> Diamond
      const s = isFocused ? 5.8 : 4.8;
      return (
        <polygon
          points={`${x},${y - s} ${x + s},${y} ${x},${y + s} ${x - s},${y}`}
          fill={color}
          stroke={bgFill}
          strokeWidth="1.5"
        />
      );
    }

    return (
      <circle
        cx={x}
        cy={y}
        r={isFocused ? 4.8 : 3.6}
        fill={color}
        stroke={bgFill}
        strokeWidth="1.5"
      />
    );
  };

  return (
    <div className={`w-full overflow-x-auto rounded-2xl border transition-all duration-300 shadow-xl ${isDarkMode
        ? 'bg-[#06080d]/90 border-white/10'
        : 'bg-white border-slate-200'
      }`}>
      <div className="min-w-[960px] p-4 md:p-6 select-none relative overflow-hidden">
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

          {/* Single Model Indicator */}
          {isSingleModel && singleModel && (
            <g transform={`translate(${viewBoxWidth / 2}, 54)`}>
              <line x1={-60} y1={0} x2={-44} y2={0} stroke={singleModel.color} strokeWidth="2.8" />
              <circle cx={-52} cy={0} r={4} fill={singleModel.color} />
              <text x={-36} y={3.5} fill={textColor} fontSize="11" fontWeight="700">
                {singleModel.modelName} (Single Model Trajectory)
              </text>
            </g>
          )}

          {/* Legend Banner (when comparing 2+ models OR 3 phases) */}
          {!isSingleModel && trajectories && trajectories.length > 0 && (
            <g transform={`translate(${viewBoxWidth / 2}, 54)`}>
              {(() => {
                const itemSpacing = isPhaseMode ? 220 : 180;
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
                      {/* Geometric marker representation */}
                      {isPhaseMode ? (
                        traj.modelId === 'phase1' ? (
                          <circle cx={8} cy={0} r={4.5} fill={traj.color} />
                        ) : traj.modelId === 'phase2' ? (
                          <rect x={4.5} y={-3.5} width={7} height={7} fill={traj.color} />
                        ) : (
                          <polygon points="8,-4.5 12.5,0 8,4.5 3.5,0" fill={traj.color} />
                        )
                      ) : (
                        <circle cx={8} cy={0} r={4} fill={traj.color} />
                      )}
                      <text x={24} y={3.5} fill={isHovered ? traj.color : textColor} fontSize="11" fontWeight="700">
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
                          seriesId: traj.modelId,
                          seriesName: traj.modelName,
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
                        {renderPointMarker(traj.modelId, x, y, traj.color, isFocused)}
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
              {isPhaseMode ? `Routing Latency (${latencyMetric.toUpperCase()}) (ms)` : 'Routing Latency (ms)'}
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

            {/* If Single Model: dual-curve (P50 & Mean) */}
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
                            <text x={x} y={y - 7} textAnchor="middle" fill={subtextColor} fontSize="7.5" fontWeight="600">
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

            {/* If Multi-Model or Phase Comparison: Plot each trajectory line */}
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
                          seriesId: traj.modelId,
                          seriesName: traj.modelName,
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
                        {renderPointMarker(traj.modelId, x, y, traj.color, isFocused)}
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

            {/* Y-Grid Ticks for Tokens */}
            {(() => {
              const step = panel3Max <= 20 ? 5 : panel3Max <= 1000 ? 250 : 1000;
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
                      {tick >= 1000 ? `${(tick / 1000).toFixed(0)}k` : tick}
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
                          seriesId: traj.modelId,
                          seriesName: traj.modelName,
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
                        {renderPointMarker(traj.modelId, x, y, traj.color, isFocused)}
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

            {/* Y-Grid Ticks for Cumulative Tokens (dynamic step calculation producing 4-5 clean ticks) */}
            {(() => {
              const step = panel4Max <= 50 ? 10 : panel4Max <= 200000 ? 50000 : panel4Max <= 1000000 ? 250000 : 500000;
              const ticks = [];
              for (let t = 0; t <= panel4Max; t += step) {
                ticks.push(t);
              }
              return ticks.map((tick) => {
                const yPos = plotHeight - (tick / panel4Max) * plotHeight;
                const label = tick >= 1000000 ? `${(tick / 1000000).toFixed(1)}M` : tick >= 1000 ? `${(tick / 1000).toFixed(0)}k` : `${tick}`;
                return (
                  <g key={`p4-grid-${tick}`}>
                    <line x1={0} y1={yPos} x2={panelWidth} y2={yPos} stroke={gridLineColor} strokeDasharray="3 3" strokeWidth="1" />
                    <text x={-6} y={yPos + 3.5} textAnchor="end" fill={subtextColor} fontSize="8" fontWeight="500">
                      {label}
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
            <text x={-38} y={plotHeight / 2} textAnchor="middle" fill={subtextColor} fontSize="10" fontWeight="600" transform={`rotate(-90, -38, ${plotHeight / 2})`}>
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
                          seriesId: traj.modelId,
                          seriesName: traj.modelName,
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
                        {renderPointMarker(traj.modelId, x, y, traj.color, isFocused)}
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

          {/* Clean centered empty state when no models/trajectories are selected (without collapsing height) */}
          {(!trajectories || trajectories.length === 0) && (
            <g transform={`translate(${viewBoxWidth / 2}, ${headerHeight + plotHeight / 2})`}>
              <rect
                x={-200}
                y={-34}
                width={400}
                height={68}
                rx={10}
                fill={isDarkMode ? 'rgba(10, 13, 20, 0.94)' : 'rgba(255, 255, 255, 0.95)'}
                stroke={panelBorder}
                strokeWidth="1.2"
              />
              <text
                x={0}
                y={-6}
                textAnchor="middle"
                fill={textColor}
                fontSize="13"
                fontWeight="700"
              >
                No trajectory data available
              </text>
              <text
                x={0}
                y={15}
                textAnchor="middle"
                fill={subtextColor}
                fontSize="11"
                fontWeight="500"
              >
                Select at least one router model or enable 3-phase comparison
              </text>
            </g>
          )}
        </svg>

        {/* Floating Tooltip for Interactive Inspection (anchors inward from edges to eliminate overflow jitter) */}
        {hoveredState && (() => {
          const isRightHalf = hoveredState.xPos > viewBoxWidth * 0.52;
          const leftPercent = (hoveredState.xPos / viewBoxWidth) * 100;
          const topPercent = (hoveredState.yPos / totalSvgHeight) * 100;

          return (
            <div
              className="absolute z-30 pointer-events-none rounded-xl p-3 shadow-2xl border text-xs flex flex-col gap-1 backdrop-blur-xl select-none"
              style={{
                left: `${leftPercent}%`,
                top: `${topPercent}%`,
                transform: isRightHalf ? 'translate(calc(-100% - 14px), -50%)' : 'translate(14px, -50%)',
                backgroundColor: isDarkMode ? 'rgba(10, 14, 23, 0.96)' : 'rgba(255, 255, 255, 0.98)',
                borderColor: isDarkMode ? 'rgba(255, 255, 255, 0.15)' : 'rgba(0, 0, 0, 0.15)',
                color: isDarkMode ? '#f8fafc' : '#0f172a',
                minWidth: '200px'
              }}
            >
              <div className="font-bold flex items-center justify-between gap-3 border-b pb-1 border-white/10">
                <span className="truncate">{hoveredState.seriesName}</span>
                <span className="font-mono text-cyan-400 flex-none">{hoveredState.numTools} Tools</span>
              </div>
              {isPhaseMode && comparedModelName && (
                <div className="text-[10px] text-slate-400 font-mono -mt-0.5">
                  Model: <span className={isDarkMode ? 'text-white font-semibold' : 'text-slate-900 font-semibold'}>{comparedModelName}</span>
                </div>
              )}
              <div className="grid grid-cols-2 gap-x-3 gap-y-0.5 text-[11px] pt-1 font-mono">
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
          );
        })()}
      </div>
    </div>
  );
};

export default RouterScalabilityLineChart;
