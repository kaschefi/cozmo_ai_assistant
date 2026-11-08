import React, { useState } from 'react';
import { type BenchmarkRecord, MODEL_DISPLAY_ORDER } from '../data/routerBenchmarkData';

export interface RouterBarChartProps {
  records: BenchmarkRecord[];
  phase: string;
  numTools: number;
  isDarkMode?: boolean;
}

/**
 * RouterBarChart Component
 *
 * Implements a high-precision 3-panel comparative horizontal bar chart:
 * Panel 1: Routing Accuracy (%)
 * Panel 2: Latency (ms) [Dual grouped: P50 Median & Mean]
 * Panel 3: Total LLM Tokens Used
 *
 * Recreates the publication-grade benchmark visualization from matplotlib
 * with full responsiveness, interactive tooltips, and theme support.
 *
 * Height Stability Guarantee:
 * Uses a fixed vertical frame based on maximum benchmark models so filtering
 * models in or out never causes height collapse, expansion, or layout jumps.
 */
export const RouterBarChart: React.FC<RouterBarChartProps> = ({
  records,
  phase,
  numTools,
  isDarkMode = false
}) => {
  const [hoveredModel, setHoveredModel] = useState<string | null>(null);

  // Visual layout constants - strictly fixed height to prevent layout shifts during filtering
  const viewBoxWidth = 1180;
  const rowHeight = 58;
  const headerHeight = 72;
  const footerHeight = 48;
  const maxModels = Math.max(MODEL_DISPLAY_ORDER.length, records?.length || 0); // 6
  const fixedContentHeight = maxModels * rowHeight; // 348
  const totalSvgHeight = headerHeight + fixedContentHeight + footerHeight; // 468

  // Horizontal column boundaries
  const labelWidth = 135;
  const colGap = 20;

  // 3 equal panels in remaining width
  const usableWidth = viewBoxWidth - labelWidth - (colGap * 2) - 24;
  const panelWidth = Math.floor(usableWidth / 3);

  const panel1Left = labelWidth;
  const panel2Left = panel1Left + panelWidth + colGap;
  const panel3Left = panel2Left + panelWidth + colGap;

  // Panel 1 x-axis max has 15% headroom for right-side text labels (e.g. 96.8%)
  const panel1ScaleMax = 115;

  const rawMaxLat = records && records.length > 0
    ? Math.max(...records.map(r => Math.max(r.p50LatencyMs, r.meanLatencyMs)), 100)
    : 1000;
  const panel2ScaleMax = Math.ceil(rawMaxLat * 1.25 / 250) * 250 || 2000;

  const rawMaxTokens = records && records.length > 0
    ? Math.max(...records.map(r => r.totalTokens), 1000)
    : 50000;
  const panel3ScaleMax = Math.ceil(rawMaxTokens * 1.25 / 10000) * 10000 || 100000;

  // Theme styling colors
  const bgFill = isDarkMode ? '#0a0d14' : '#ffffff';
  const panelBorder = isDarkMode ? '#1e293b' : '#334155';
  const gridLineColor = isDarkMode ? 'rgba(255, 255, 255, 0.08)' : 'rgba(0, 0, 0, 0.08)';
  const textColor = isDarkMode ? '#f8fafc' : '#0f172a';
  const subtextColor = isDarkMode ? '#94a3b8' : '#475569';

  return (
    <div className={`w-full overflow-x-auto rounded-2xl border transition-all duration-300 shadow-xl ${isDarkMode
        ? 'bg-[#06080d]/90 border-white/10'
        : 'bg-white border-slate-200'
      }`}>
      <div className="min-w-[860px] p-4 md:p-6 select-none">
        <svg
          viewBox={`0 0 ${viewBoxWidth} ${totalSvgHeight}`}
          className="w-full h-auto overflow-visible font-sans"
        >
          {/* Main Figure Title */}
          <text
            x={viewBoxWidth / 2}
            y={30}
            textAnchor="middle"
            fill={textColor}
            fontSize="17"
            fontWeight="700"
            letterSpacing="-0.01em"
          >
            MoKa Router Benchmark ({numTools} Tools) - Phase: {phase}
          </text>

          {/* =========================================================================
              PANEL 1: ROUTING ACCURACY (%)
             ========================================================================= */}
          <g transform={`translate(${panel1Left}, ${headerHeight})`}>
            {/* Subplot Title */}
            <text
              x={panelWidth / 2}
              y={-14}
              textAnchor="middle"
              fill={textColor}
              fontSize="13"
              fontWeight="700"
            >
              Routing Accuracy (%)
            </text>

            {/* Subplot Box Background & Border */}
            <rect
              x={0}
              y={0}
              width={panelWidth}
              height={fixedContentHeight}
              fill={bgFill}
              stroke={panelBorder}
              strokeWidth="1.2"
            />

            {/* Horizontal row divider guides */}
            {Array.from({ length: maxModels - 1 }).map((_, i) => (
              <line
                key={`row-sep-1-${i}`}
                x1={0}
                y1={(i + 1) * rowHeight}
                x2={panelWidth}
                y2={(i + 1) * rowHeight}
                stroke={gridLineColor}
                strokeDasharray="2 3"
                strokeWidth="0.8"
                opacity={0.6}
              />
            ))}

            {/* Grid Lines at 0, 20, 40, 60, 80, 100 */}
            {[0, 20, 40, 60, 80, 100].map((tick) => {
              const xPos = (tick / panel1ScaleMax) * panelWidth;
              return (
                <g key={`grid-acc-${tick}`}>
                  <line
                    x1={xPos}
                    y1={0}
                    x2={xPos}
                    y2={fixedContentHeight}
                    stroke={gridLineColor}
                    strokeDasharray="3 3"
                    strokeWidth="1"
                  />
                  {/* Bottom tick label */}
                  <text
                    x={xPos}
                    y={fixedContentHeight + 16}
                    textAnchor="middle"
                    fill={subtextColor}
                    fontSize="10"
                    fontWeight="500"
                  >
                    {tick}
                  </text>
                </g>
              );
            })}

            {/* X-Axis Caption */}
            <text
              x={panelWidth / 2}
              y={fixedContentHeight + 35}
              textAnchor="middle"
              fill={subtextColor}
              fontSize="11"
              fontWeight="600"
            >
              Accuracy (%)
            </text>

            {/* Bars for Accuracy */}
            {records.map((r, idx) => {
              const yCenter = idx * rowHeight + rowHeight / 2;
              const barHeight = 28;
              const barY = yCenter - barHeight / 2;
              const barWidth = Math.max(2, (r.accuracy / panel1ScaleMax) * panelWidth);
              const isHovered = hoveredModel === r.modelId;

              return (
                <g
                  key={`acc-bar-${r.modelId}`}
                  onMouseEnter={() => setHoveredModel(r.modelId)}
                  onMouseLeave={() => setHoveredModel(null)}
                  className="cursor-pointer transition-opacity duration-150"
                  opacity={hoveredModel && !isHovered ? 0.45 : 1}
                >
                  {/* Subtle row hover highlight */}
                  {isHovered && (
                    <rect
                      x={-panel1Left + 10}
                      y={idx * rowHeight}
                      width={viewBoxWidth - 20}
                      height={rowHeight}
                      fill={isDarkMode ? 'rgba(255,255,255,0.03)' : 'rgba(0,0,0,0.02)'}
                      pointerEvents="none"
                    />
                  )}

                  {/* Horizontal Accuracy Bar */}
                  <rect
                    x={0}
                    y={barY}
                    width={barWidth}
                    height={barHeight}
                    fill={r.color}
                    stroke={panelBorder}
                    strokeWidth="1"
                    rx={2}
                  />

                  {/* Percentage Value Label on the right of bar */}
                  <text
                    x={barWidth + 6}
                    y={yCenter + 4}
                    fill={textColor}
                    fontSize="11"
                    fontWeight="700"
                  >
                    {r.accuracy.toFixed(1)}%
                  </text>
                </g>
              );
            })}
          </g>

          {/* Model Names (Left Y-Axis Labels aligned with Panel 1) */}
          <g transform={`translate(${panel1Left - 12}, ${headerHeight})`}>
            {records.map((r, idx) => {
              const yCenter = idx * rowHeight + rowHeight / 2;
              const isHovered = hoveredModel === r.modelId;

              return (
                <text
                  key={`label-${r.modelId}`}
                  x={0}
                  y={yCenter + 4}
                  textAnchor="end"
                  fill={isHovered ? r.color : textColor}
                  fontSize="11.5"
                  fontWeight="700"
                  className="cursor-pointer transition-colors"
                  onMouseEnter={() => setHoveredModel(r.modelId)}
                  onMouseLeave={() => setHoveredModel(null)}
                >
                  {r.modelName}
                </text>
              );
            })}
          </g>

          {/* =========================================================================
              PANEL 2: LATENCY (ms) - Dual Bar (P50 Median & Mean)
             ========================================================================= */}
          <g transform={`translate(${panel2Left}, ${headerHeight})`}>
            {/* Subplot Title */}
            <text
              x={panelWidth / 2}
              y={-14}
              textAnchor="middle"
              fill={textColor}
              fontSize="13"
              fontWeight="700"
            >
              Latency (ms)
            </text>

            {/* Subplot Box Background & Border */}
            <rect
              x={0}
              y={0}
              width={panelWidth}
              height={fixedContentHeight}
              fill={bgFill}
              stroke={panelBorder}
              strokeWidth="1.2"
            />

            {/* Horizontal row divider guides */}
            {Array.from({ length: maxModels - 1 }).map((_, i) => (
              <line
                key={`row-sep-2-${i}`}
                x1={0}
                y1={(i + 1) * rowHeight}
                x2={panelWidth}
                y2={(i + 1) * rowHeight}
                stroke={gridLineColor}
                strokeDasharray="2 3"
                strokeWidth="0.8"
                opacity={0.6}
              />
            ))}

            {/* Grid Lines for Latency */}
            {(() => {
              const step = panel2ScaleMax <= 1000 ? 200 : panel2ScaleMax <= 2000 ? 250 : 500;
              const ticks = [];
              for (let t = 0; t <= panel2ScaleMax; t += step) {
                ticks.push(t);
              }
              return ticks.map((tick) => {
                const xPos = (tick / panel2ScaleMax) * panelWidth;
                return (
                  <g key={`grid-lat-${tick}`}>
                    <line
                      x1={xPos}
                      y1={0}
                      x2={xPos}
                      y2={fixedContentHeight}
                      stroke={gridLineColor}
                      strokeDasharray="3 3"
                      strokeWidth="1"
                    />
                    <text
                      x={xPos}
                      y={fixedContentHeight + 16}
                      textAnchor="middle"
                      fill={subtextColor}
                      fontSize="10"
                      fontWeight="500"
                    >
                      {tick}
                    </text>
                  </g>
                );
              });
            })()}

            {/* X-Axis Caption */}
            <text
              x={panelWidth / 2}
              y={fixedContentHeight + 35}
              textAnchor="middle"
              fill={subtextColor}
              fontSize="11"
              fontWeight="600"
            >
              Milliseconds (ms)
            </text>

            {/* Dual Bars for P50 & Mean Latency */}
            {records.map((r, idx) => {
              const yCenter = idx * rowHeight + rowHeight / 2;
              const barHeight = 14;
              const p50Y = yCenter - barHeight - 1;
              const meanY = yCenter + 1;

              const p50Width = Math.max(2, (r.p50LatencyMs / panel2ScaleMax) * panelWidth);
              const meanWidth = Math.max(2, (r.meanLatencyMs / panel2ScaleMax) * panelWidth);
              const isHovered = hoveredModel === r.modelId;

              return (
                <g
                  key={`lat-bar-${r.modelId}`}
                  onMouseEnter={() => setHoveredModel(r.modelId)}
                  onMouseLeave={() => setHoveredModel(null)}
                  className="cursor-pointer transition-opacity duration-150"
                  opacity={hoveredModel && !isHovered ? 0.45 : 1}
                >
                  {/* Top Bar: P50 (Median) - Darker Emerald/Teal (#059669) */}
                  <rect
                    x={0}
                    y={p50Y}
                    width={p50Width}
                    height={barHeight}
                    fill="#059669"
                    stroke="#064E3B"
                    strokeWidth="0.8"
                    rx={1.5}
                  />
                  <text
                    x={p50Width + 4}
                    y={p50Y + 11}
                    fill={textColor}
                    fontSize="9"
                    fontWeight="600"
                  >
                    {Math.round(r.p50LatencyMs)}ms
                  </text>

                  {/* Bottom Bar: Mean - Lighter Emerald (#34D399) */}
                  <rect
                    x={0}
                    y={meanY}
                    width={meanWidth}
                    height={barHeight}
                    fill="#34D399"
                    stroke="#064E3B"
                    strokeWidth="0.8"
                    rx={1.5}
                  />
                  <text
                    x={meanWidth + 4}
                    y={meanY + 11}
                    fill={textColor}
                    fontSize="9"
                    fontWeight="600"
                  >
                    {Math.round(r.meanLatencyMs)}ms
                  </text>
                </g>
              );
            })}

            {/* Top-right Legend for Latency (placed at top-right to prevent obscuring high-latency bar labels) */}
            <g transform={`translate(${panelWidth - 110}, 8)`}>
              <rect
                x={0}
                y={0}
                width={104}
                height={36}
                fill={isDarkMode ? 'rgba(15, 23, 42, 0.94)' : 'rgba(255, 255, 255, 0.96)'}
                stroke={panelBorder}
                strokeWidth="0.8"
                rx={4}
              />
              {/* P50 Legend entry */}
              <rect x={7} y={7} width={10} height={8} fill="#059669" stroke="#064E3B" strokeWidth="0.5" rx={1} />
              <text x={22} y={14} fill={textColor} fontSize="8.5" fontWeight="600">P50 (Median)</text>
              {/* Mean Legend entry */}
              <rect x={7} y={20} width={10} height={8} fill="#34D399" stroke="#064E3B" strokeWidth="0.5" rx={1} />
              <text x={22} y={27} fill={textColor} fontSize="8.5" fontWeight="600">Mean</text>
            </g>
          </g>

          {/* =========================================================================
              PANEL 3: TOTAL LLM TOKENS USED
             ========================================================================= */}
          <g transform={`translate(${panel3Left}, ${headerHeight})`}>
            {/* Subplot Title */}
            <text
              x={panelWidth / 2}
              y={-14}
              textAnchor="middle"
              fill={textColor}
              fontSize="13"
              fontWeight="700"
            >
              Total LLM Tokens Used
            </text>

            {/* Subplot Box Background & Border */}
            <rect
              x={0}
              y={0}
              width={panelWidth}
              height={fixedContentHeight}
              fill={bgFill}
              stroke={panelBorder}
              strokeWidth="1.2"
            />

            {/* Horizontal row divider guides */}
            {Array.from({ length: maxModels - 1 }).map((_, i) => (
              <line
                key={`row-sep-3-${i}`}
                x1={0}
                y1={(i + 1) * rowHeight}
                x2={panelWidth}
                y2={(i + 1) * rowHeight}
                stroke={gridLineColor}
                strokeDasharray="2 3"
                strokeWidth="0.8"
                opacity={0.6}
              />
            ))}

            {/* Grid Lines for Tokens (subtle dashed guidelines, no scale numbers at bottom per request) */}
            {(() => {
              const step = panel3ScaleMax <= 50000 ? 10000 : 20000;
              const ticks = [];
              for (let t = 0; t <= panel3ScaleMax; t += step) {
                ticks.push(t);
              }
              return ticks.map((tick) => {
                const xPos = (tick / panel3ScaleMax) * panelWidth;
                return (
                  <g key={`grid-tok-${tick}`}>
                    <line
                      x1={xPos}
                      y1={0}
                      x2={xPos}
                      y2={fixedContentHeight}
                      stroke={gridLineColor}
                      strokeDasharray="3 3"
                      strokeWidth="1"
                    />
                  </g>
                );
              });
            })()}

            {/* X-Axis Caption */}
            <text
              x={panelWidth / 2}
              y={fixedContentHeight + 35}
              textAnchor="middle"
              fill={subtextColor}
              fontSize="11"
              fontWeight="600"
            >
              Tokens Count
            </text>

            {/* Bars for Total Tokens */}
            {records.map((r, idx) => {
              const yCenter = idx * rowHeight + rowHeight / 2;
              const barHeight = 28;
              const barY = yCenter - barHeight / 2;
              const barWidth = r.totalTokens > 0
                ? Math.max(3, (r.totalTokens / panel3ScaleMax) * panelWidth)
                : 0;
              const isHovered = hoveredModel === r.modelId;

              const labelText = r.isLaya || r.totalTokens === 0
                ? '0 (LAYA)'
                : r.totalTokens.toLocaleString();

              return (
                <g
                  key={`tok-bar-${r.modelId}`}
                  onMouseEnter={() => setHoveredModel(r.modelId)}
                  onMouseLeave={() => setHoveredModel(null)}
                  className="cursor-pointer transition-opacity duration-150"
                  opacity={hoveredModel && !isHovered ? 0.45 : 1}
                >
                  {/* Purple Horizontal Bar */}
                  {r.totalTokens > 0 && (
                    <rect
                      x={0}
                      y={barY}
                      width={barWidth}
                      height={barHeight}
                      fill="#8B5CF6"
                      stroke="#4C1D95"
                      strokeWidth="1"
                      rx={2}
                    />
                  )}

                  {/* Token Count Label */}
                  <text
                    x={barWidth + 6}
                    y={yCenter + 4}
                    fill={textColor}
                    fontSize="10.5"
                    fontWeight="700"
                  >
                    {labelText}
                  </text>
                </g>
              );
            })}
          </g>

          {/* Clean centered empty state when no models are selected (without collapsing height) */}
          {(!records || records.length === 0) && (
            <g transform={`translate(${viewBoxWidth / 2}, ${headerHeight + fixedContentHeight / 2})`}>
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
                No models selected to display
              </text>
              <text
                x={0}
                y={15}
                textAnchor="middle"
                fill={subtextColor}
                fontSize="11"
                fontWeight="500"
              >
                Enable at least one model from the filter below to view results
              </text>
            </g>
          )}
        </svg>
      </div>
    </div>
  );
};

export default RouterBarChart;
