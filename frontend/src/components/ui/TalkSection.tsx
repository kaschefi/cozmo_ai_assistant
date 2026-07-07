import React from 'react';

export const TalkSection: React.FC = () => {
  return (
    <div
      id="talk-section"
      className="w-full py-24 border-t border-slate-900/60 flex flex-col md:flex-row items-center justify-between gap-12 min-h-[50vh] relative z-20"
    >
      {/* Left Column: Interactive Button & Call to Action */}
      <div className="flex flex-col items-start gap-6 md:w-1/2">
        <div className="inline-block text-[11px] font-extrabold text-cyan-400 uppercase tracking-[0.2em] px-3 py-1 bg-cyan-950/40 rounded-full border border-cyan-500/20">
          Voice Interface
        </div>
        <h2 className="text-3xl md:text-4xl font-extrabold text-white tracking-tight leading-tight">
          Talk to Moka
        </h2>
        <p className="text-slate-400 text-sm md:text-base leading-relaxed max-w-md mb-2">
          Initiate a natural voice conversation with your agent. Moka listens for commands, manages schedules, and responds vocally with real-time speech synthesis.
        </p>

        {/* Target button for the swarming particle halo */}
        <button
          id="talk-button"
          className="relative px-8 py-4 rounded-xl bg-slate-950/50 border border-cyan-500/50 hover:border-cyan-400 text-white font-bold tracking-wide shadow-[0_0_20px_rgba(0,243,255,0.15)] hover:shadow-[0_0_30px_rgba(0,243,255,0.3)] transition-all duration-300 hover:scale-[1.02] active:scale-95 flex items-center gap-3 cursor-pointer"
        >
          <svg className="w-5 h-5 text-cyan-400 animate-pulse" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z" />
          </svg>
          <span>Initialize Assistant</span>
        </button>
      </div>

      {/* Right Column: Key Details & Features */}
      <div className="grid grid-cols-1 gap-6 md:w-1/2">
        <div className="p-6 rounded-xl bg-slate-900/25 border border-slate-800/40 backdrop-blur-sm hover:border-slate-700/40 transition-colors duration-300">
          <h4 className="text-white font-bold text-sm mb-1">Google Speech Recognition</h4>
          <p className="text-slate-400 text-xs leading-relaxed">
            Accurate wake-word and command translation routing directly to fast semantic reflex matching or multi-agent pipelines.
          </p>
        </div>
        <div className="p-6 rounded-xl bg-slate-900/25 border border-slate-800/40 backdrop-blur-sm hover:border-slate-700/40 transition-colors duration-300">
          <h4 className="text-white font-bold text-sm mb-1">Studio Quality Speech Synthesis</h4>
          <p className="text-slate-400 text-xs leading-relaxed">
            Near-instant response streaming using local Kokoro-ONNX voice execution on asynchronous threads.
          </p>
        </div>
      </div>
    </div>
  );
};

export default TalkSection;
