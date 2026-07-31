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
      <div className="relative inline-block">
        <h2 className="text-3xl md:text-4xl font-extrabold text-white tracking-tight leading-tight">
          Talk to Moka
        </h2>
        <svg
          className="absolute -bottom-3 -left-2 w-[calc(100%+1rem)] h-3.5 text-[#00d2ff] drop-shadow-[0_0_8px_rgba(0,210,255,0.85)]"
          viewBox="0 0 300 20"
          fill="none"
          preserveAspectRatio="none"
          xmlns="http://www.w3.org/2000/svg"
        >
          <path
            d="M 10 14 C 50 4, 100 18, 150 12 C 200 6, 250 16, 290 8"
            stroke="currentColor"
            strokeWidth="4"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
      </div>
      <p className="text-slate-400 text-sm md:text-base leading-relaxed max-w-3xl mt-2">
        Initiate a natural voice conversation with your agent. Moka listens for commands, manages schedules, and responds vocally with real-time speech synthesis.
      </p>

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
