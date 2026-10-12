import React from 'react';

interface AgentCoreStateProps {
  isHovered: boolean;
}

export const AgentCoreState: React.FC<AgentCoreStateProps> = ({ isHovered }) => {
  return (
    <div className="relative w-full h-[220px] md:h-[260px] flex items-center justify-center rounded-2xl bg-slate-950/10 border border-slate-900/35 backdrop-blur-sm overflow-hidden">
      
      {/* Local keyframe animations for the smooth organic soundwave ripples */}
      <style>{`
        @keyframes voice-ripple {
          0% {
            transform: scale(0.85);
            opacity: 0.8;
          }
          100% {
            transform: scale(2.2);
            opacity: 0;
          }
        }
        .voice-wave {
          animation: voice-ripple 2.4s cubic-bezier(0.16, 1, 0.3, 1) infinite;
        }
      `}</style>

      {/* Subtle background radial glow */}
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,transparent_60%,rgba(2,5,18,0.2)_100%)] pointer-events-none" />

      {/* Ripple Animation Container */}
      <div className="relative flex items-center justify-center w-40 h-40">
        
        {/* Dynamic expanding voice ripples when hovered */}
        {isHovered ? (
          <>
            <div className="absolute inset-0 rounded-full border border-[#00d2ff]/30 voice-wave pointer-events-none" style={{ animationDelay: '0s' }} />
            <div className="absolute inset-0 rounded-full border border-[#00d2ff]/20 voice-wave pointer-events-none" style={{ animationDelay: '0.8s' }} />
            <div className="absolute inset-0 rounded-full border border-[#00d2ff]/10 voice-wave pointer-events-none" style={{ animationDelay: '1.6s' }} />
          </>
        ) : (
          // Soft static rings when standby
          <>
            <div className="absolute w-28 h-28 rounded-full border border-slate-800/40 pointer-events-none transition-all duration-700" />
            <div className="absolute w-36 h-36 rounded-full border border-slate-900/30 pointer-events-none transition-all duration-700" />
          </>
        )}

        {/* Central Speech Core Button */}
        <div className={`z-10 flex items-center justify-center rounded-full bg-slate-950/80 border transition-all duration-500 ${
          isHovered 
            ? 'w-20 h-20 border-[#00d2ff] shadow-[0_0_35px_rgba(0,210,255,0.45)] scale-105' 
            : 'w-16 h-16 border-slate-800 shadow-[0_0_15px_rgba(0,0,0,0.45)]'
        }`}>
          <svg 
            className={`w-7 h-7 transition-all duration-500 ${
              isHovered ? 'text-[#00d2ff] drop-shadow-[0_0_6px_#00d2ff]' : 'text-slate-400'
            }`} 
            fill="none" 
            viewBox="0 0 24 24" 
            stroke="currentColor" 
            strokeWidth={1.5}
          >
            <path 
              strokeLinecap="round" 
              strokeLinejoin="round" 
              d="M12 18.75a6 6 0 006-6v-1.5m-6 7.5a6 6 0 01-6-6v-1.5m6 7.5v3.75m-3.75 0h7.5M12 15.75a3 3 0 01-3-3V4.5a3 3 0 116 0v8.25a3 3 0 01-3 3z" 
            />
          </svg>
        </div>
      </div>

      {/* Minimal status sub-label */}
      <div className="absolute bottom-4 text-[9px] uppercase tracking-[0.25em] font-mono text-slate-500 transition-colors duration-500">
        {isHovered ? (
          <span className="text-[#00d2ff] animate-pulse">Connection Ready</span>
        ) : (
          <span>Voice Link Idle</span>
        )}
      </div>

    </div>
  );
};

export default AgentCoreState;
