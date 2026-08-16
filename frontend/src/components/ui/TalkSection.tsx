import React from 'react';

interface TalkSectionProps {
  onStartChat?: () => void;
}

export const TalkSection: React.FC<TalkSectionProps> = ({ onStartChat }) => {
  return (
    <div
      id="talk-section"
      className="w-full py-24 border-t border-slate-900/60 flex flex-col items-start gap-6 min-h-[40vh] relative z-20"
    >
      <div className="flex flex-col items-start gap-2">
        <div className="relative inline-block mb-1">
          <h2 className="font-megrim text-4xl md:text-5xl text-white tracking-wider leading-tight">
            Talk to Moka
          </h2>
          <div className="brand-underline" />
        </div>
        <p className="text-slate-400 text-sm md:text-base leading-relaxed max-w-3xl mt-2 font-sans">
          Initiate a natural voice conversation with your agent. Moka listens for commands, manages schedules, and responds vocally with real-time speech synthesis.
        </p>
      </div>

      {/* Target button for the swarming particle halo */}
      <button
        id="talk-button"
        onClick={onStartChat}
        className="relative px-8 py-4 rounded-xl bg-slate-950/50 border border-cyan-500/50 hover:border-cyan-400 text-white font-bold tracking-wide shadow-[0_0_20px_rgba(0,243,255,0.15)] hover:shadow-[0_0_30px_rgba(0,243,255,0.3)] transition-all duration-300 hover:scale-[1.02] active:scale-95 flex items-center gap-3 cursor-pointer mt-2"
      >
        <svg className="w-5 h-5 text-cyan-400 animate-pulse" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z" />
        </svg>
        <span>Start a conversation</span>
      </button>
    </div>
  );
};

export default TalkSection;
