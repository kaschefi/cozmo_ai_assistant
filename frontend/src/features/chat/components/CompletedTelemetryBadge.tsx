import React, { useState } from 'react';
import type { MessageTelemetry } from '../services/chatHistory';

interface CompletedTelemetryBadgeProps {
  telemetry: MessageTelemetry;
}

export const CompletedTelemetryBadge: React.FC<CompletedTelemetryBadgeProps> = ({ telemetry }) => {
  const [isExpanded, setIsExpanded] = useState(false);

  const friendlyToolName = (tool?: string) => {
    if (!tool || tool === 'none') return null;
    if (tool.includes('calendar')) return 'Calendar Agent';
    if (tool.includes('weather')) return 'Weather Telemetry';
    if (tool.includes('search')) return 'Web Search';
    if (tool.includes('code')) return 'Code Sandbox';
    if (tool.includes('todo')) return 'To-Do List';
    if (tool.includes('date')) return 'System Clock';
    if (tool.includes('joke')) return 'Reflex Engine';
    return tool.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
  };

  const toolDisplay = friendlyToolName(telemetry.tool);
  const elapsed = telemetry.elapsedSeconds !== undefined ? `${telemetry.elapsedSeconds.toFixed(1)}s` : null;
  const providerDisplay = telemetry.provider === 'cloud' ? 'Azure Cloud' : 'Local Brain';

  return (
    <div className="flex flex-col gap-1 mb-2">
      <button
        type="button"
        onClick={() => setIsExpanded(prev => !prev)}
        className="inline-flex items-center gap-1.5 self-start px-2 py-0.5 rounded-full bg-white/[0.03] hover:bg-white/[0.06] border border-white/[0.08] text-[9px] font-mono text-slate-400 hover:text-slate-200 transition-all cursor-pointer"
        title="Click to view cognitive execution details"
      >
        <span className="w-1.5 h-1.5 rounded-full bg-white/60" />
        <span>Thought {elapsed ? `for ${elapsed}` : 'complete'}</span>
        {toolDisplay && (
          <>
            <span className="text-white/20">·</span>
            <span className="text-white/80 font-medium">{toolDisplay}</span>
          </>
        )}
        <span className="text-white/20">·</span>
        <span>{providerDisplay}</span>
        <svg
          className={`w-2.5 h-2.5 text-slate-500 transition-transform duration-200 ${isExpanded ? 'rotate-180' : ''}`}
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          strokeWidth={2}
        >
          <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {isExpanded && (
        <div className="p-2.5 rounded-xl bg-white/[0.02] border border-white/[0.06] text-[10px] font-mono text-slate-400 space-y-1 animate-fadeIn max-w-sm">
          <div className="flex items-center justify-between text-slate-500 pb-1 border-b border-white/[0.04]">
            <span>Cognitive Routing Pipeline</span>
            <span>{elapsed}</span>
          </div>
          <div className="space-y-0.5 pt-0.5">
            <div className="flex items-center gap-1.5 text-slate-300">
              <span className="text-white">✓</span>
              <span>1. Long-Term Memory & Profile Recall</span>
            </div>
            <div className="flex items-center gap-1.5 text-slate-300">
              <span className="text-white">✓</span>
              <span>2. Vector Intent & Tool Router</span>
            </div>
            <div className="flex items-center gap-1.5 text-slate-300">
              <span className="text-white">✓</span>
              <span>3. {toolDisplay ? `Executed: ${toolDisplay}` : 'Conversational Neural Routing'}</span>
            </div>
            <div className="flex items-center gap-1.5 text-slate-300">
              <span className="text-white">✓</span>
              <span>4. Final Natural Dialogue Synthesis</span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
