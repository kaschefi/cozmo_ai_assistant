import React from 'react';

/**
 * WelcomeCard component representing the central introduction block of the Moka ecosystem.
 */
export const WelcomeCard: React.FC = () => {
  return (
    <div className="p-12 rounded-3xl bg-slate-950/40 border border-slate-800/80 backdrop-blur-lg shadow-[0_20px_50px_rgba(0,0,0,0.6)] text-center mb-16">
      <h2 className="text-3xl font-extrabold text-white mb-4 tracking-tight">
        Welcome to the Moka Ecosystem
      </h2>
      <p className="text-slate-300 max-w-2xl mx-auto text-base leading-relaxed mb-8">
        A state-of-the-art multi-agent intelligence platform. Scroll down to manage your workflows, configure AI models, and view task execution metrics.
      </p>
      <button className="px-8 py-3 rounded-lg bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-white font-semibold shadow-[0_0_20px_rgba(0,243,255,0.3)] transition-all duration-300 hover:scale-[1.02] cursor-pointer">
        Access Control Center
      </button>
    </div>
  );
};

export default WelcomeCard;
