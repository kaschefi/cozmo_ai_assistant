import React from 'react';
import { ThinkingOrb, type OrbState } from 'thinking-orbs';

export interface TelemetryData {
  stage: 'intent' | 'reflex' | 'memory' | 'memory_done' | 'tools_rag' | 'tools_matched' | 'routed' | 'executing' | 'synthesizing' | 'idle';
  title: string;
  text: string;
  step: number; // 1: Memory & Context, 2: Intent & Routing, 3: Action / Tool Execution, 4: Synthesis
  tool?: string;
  provider?: string;
  elapsedSeconds: number;
}

interface CognitiveTelemetryCardProps {
  telemetry: TelemetryData;
}

export const CognitiveTelemetryCard: React.FC<CognitiveTelemetryCardProps> = ({ telemetry }) => {
  // Map telemetry stage to the best ThinkingOrb state
  const getOrbState = (): OrbState => {
    switch (telemetry.stage) {
      case 'memory':
      case 'memory_done':
      case 'tools_rag':
      case 'tools_matched':
        return 'searching';
      case 'intent':
      case 'routed':
        return 'solving';
      case 'executing':
      case 'reflex':
        return 'connecting';
      case 'synthesizing':
        return 'composing';
      default:
        return 'solving';
    }
  };

  const friendlyToolName = (tool?: string) => {
    if (!tool || tool === 'none') return null;
    if (tool.includes('calendar')) return 'Calendar Agent';
    if (tool.includes('weather')) return 'Weather Telemetry';
    if (tool.includes('search')) return 'Web Search Agent';
    if (tool.includes('code')) return 'Code Sandbox';
    if (tool.includes('todo')) return 'To-Do List Agent';
    if (tool.includes('date')) return 'System Clock';
    if (tool.includes('joke')) return 'Reflex Engine';
    return tool.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
  };

  const toolDisplay = friendlyToolName(telemetry.tool);

  // Pipeline Steps Definition
  const steps = [
    { num: 1, label: 'Memory' },
    { num: 2, label: 'Router' },
    { num: 3, label: toolDisplay || 'Action' },
    { num: 4, label: 'Synthesis' },
  ];

  const currentStep = telemetry.step || 1;

  return (
    <div className="flex items-center gap-4 py-1.5 max-w-xl transition-all duration-300">
      {/* Dynamic Thinking Orb */}
      <div className="flex-shrink-0 flex items-center justify-center">
        <ThinkingOrb state={getOrbState()} size={64} />
      </div>

      {/* Cognitive Telemetry Content */}
      <div className="flex flex-col gap-2 min-w-[240px] sm:min-w-[280px] flex-1">
        {/* Dynamic Thought / Stage Description */}
        <p className="text-sm text-slate-200 font-sans leading-relaxed tracking-wide">
          {telemetry.text || 'Processing query through cognitive layer...'}
        </p>

        {/* Tool Callout Badge (if specialized tool selected) */}
        {toolDisplay && (
          <div className="inline-flex items-center gap-1.5 self-start px-2 py-0.5 rounded-md bg-white/[0.05] border border-white/[0.1] text-[10px] font-mono text-white/90">
            <svg className="w-3 h-3 text-white/70" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M13 10V3L4 14h7v7l9-11h-7z" />
            </svg>
            <span>Agent: <strong className="text-white font-medium">{toolDisplay}</strong></span>
          </div>
        )}

        {/* Multi-step Progressive Stepper */}
        <div className="flex items-center gap-1.5 pt-1.5 border-t border-white/[0.08]">
          {steps.map((st, idx) => {
            const isDone = currentStep > st.num;
            const isActive = currentStep === st.num;

            return (
              <React.Fragment key={st.num}>
                <div className="flex items-center gap-1">
                  <div
                    className={`w-3.5 h-3.5 rounded-full flex items-center justify-center text-[8px] font-mono transition-all ${
                      isDone
                        ? 'bg-white text-black font-bold'
                        : isActive
                        ? 'bg-white/20 text-white border border-white/60 animate-pulse font-semibold'
                        : 'bg-white/[0.04] text-slate-500 border border-white/[0.08]'
                    }`}
                  >
                    {isDone ? '✓' : st.num}
                  </div>
                  <span
                    className={`text-[9px] font-mono tracking-tight transition-colors ${
                      isDone
                        ? 'text-slate-300'
                        : isActive
                        ? 'text-white font-medium'
                        : 'text-slate-600'
                    }`}
                  >
                    {st.label}
                  </span>
                </div>
                {idx < steps.length - 1 && (
                  <div
                    className={`h-[1px] flex-1 min-w-[8px] transition-colors ${
                      isDone ? 'bg-white/40' : 'bg-white/[0.06]'
                    }`}
                  />
                )}
              </React.Fragment>
            );
          })}
        </div>
      </div>
    </div>
  );
};
