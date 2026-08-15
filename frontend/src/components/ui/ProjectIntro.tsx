import React from 'react';

/**
 * ProjectIntro component representing the core cognitive and infrastructure layers of Moka.
 * Restored to original layout with Google Font 'Megrim' for titles.
 */
export const ProjectIntro: React.FC = () => {
  return (
    <section className="w-full bg-transparent py-20 relative overflow-hidden border-y border-slate-900/80">
      {/* Ambient background glows */}
      <div className="absolute -top-40 -left-40 w-96 h-96 bg-cyan-950/20 rounded-full blur-[120px] pointer-events-none" />
      <div className="absolute -bottom-40 -right-40 w-96 h-96 bg-blue-950/20 rounded-full blur-[120px] pointer-events-none" />

      <div className="grid grid-cols-1 md:grid-cols-2 gap-12 max-w-6xl mx-auto px-6 relative z-10 items-center">

        {/* Left Column: Project Overview */}
        <div className="flex flex-col justify-center items-start">
          <div className="relative inline-block mb-6">
            <h2 className="font-megrim text-4xl md:text-5xl font-bold text-white tracking-wider leading-tight">
              About the Project
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
          <p className="text-slate-300 text-lg leading-relaxed mt-2">
            <strong>MoKa AI Assistant</strong> is an advanced local AI companion system designed around the <strong>Anki Cozmo</strong> robot. It merges direct physical embodiment with state-of-the-art conversational AI, creating a desktop robot that doesn't just respond to commands, but actively interacts with your daily digital life.
          </p>
          <p className="text-slate-400 text-base leading-relaxed mt-4">
            By combining high-speed semantic reflex loops with advanced reasoning models, MoKa manages schedules, tracks context, runs local workspace scripts, and connects with hardware features. It bridges the gap between mechanical robotics and cognitive AI logic.
          </p>
        </div>

        {/* Right Column: Project Goals Grid */}
        <div className="flex flex-col gap-6">
          <h3 className="font-megrim text-2xl md:text-3xl font-semibold text-slate-200 tracking-wider border-b border-slate-800 pb-2">
            Core Project Goals
          </h3>

          {/* Goal 1 */}
          <div className="group relative bg-slate-900/35 border border-slate-800/80 rounded-2xl p-5 backdrop-blur-md hover:bg-slate-900/60 hover:border-[#00d2ff]/40 hover:shadow-[0_0_25px_rgba(0,210,255,0.08)] transition-all duration-300">
            <div className="flex items-start gap-4">
              <div className="p-3 bg-slate-950/80 rounded-xl border border-slate-800/85 group-hover:border-[#00d2ff]/30 transition-colors">
                <svg className="w-5 h-5 text-[#00d2ff]" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
                </svg>
              </div>
              <div>
                <h4 className="text-white font-semibold text-base group-hover:text-[#00d2ff] transition-colors">100% Local Privacy</h4>
                <p className="text-slate-400 text-sm mt-1">
                  Run all LLMs, computer vision, vector storage, and long-term memory retrieval completely offline to secure personal data.
                </p>
              </div>
            </div>
          </div>

          {/* Goal 2 */}
          <div className="group relative bg-slate-900/35 border border-slate-800/80 rounded-2xl p-5 backdrop-blur-md hover:bg-slate-900/60 hover:border-[#00d2ff]/40 hover:shadow-[0_0_25px_rgba(0,210,255,0.08)] transition-all duration-300">
            <div className="flex items-start gap-4">
              <div className="p-3 bg-slate-950/80 rounded-xl border border-slate-800/85 group-hover:border-[#00d2ff]/30 transition-colors">
                <svg className="w-5 h-5 text-[#00d2ff]" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M13 10V3L4 14h7v7l9-11h-7z" />
                </svg>
              </div>
              <div>
                <h4 className="text-white font-semibold text-base group-hover:text-[#00d2ff] transition-colors">Dual-Layered Intellect</h4>
                <p className="text-slate-400 text-sm mt-1">
                  Combine high-speed, sub-50ms semantic routers for reflex commands with complex reasoning models for autonomous workflows.
                </p>
              </div>
            </div>
          </div>

          {/* Goal 3 */}
          <div className="group relative bg-slate-900/35 border border-slate-800/80 rounded-2xl p-5 backdrop-blur-md hover:bg-slate-900/60 hover:border-[#00d2ff]/40 hover:shadow-[0_0_25px_rgba(0,210,255,0.08)] transition-all duration-300">
            <div className="flex items-start gap-4">
              <div className="p-3 bg-slate-950/80 rounded-xl border border-slate-800/85 group-hover:border-[#00d2ff]/30 transition-colors">
                <svg className="w-5 h-5 text-[#00d2ff]" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z" />
                </svg>
              </div>
              <div>
                <h4 className="text-white font-semibold text-base group-hover:text-[#00d2ff] transition-colors">Empathetic Companion Core</h4>
                <p className="text-slate-400 text-sm mt-1">
                  Develop persistent biographical learning models allowing the robot to remember preferences and context over time.
                </p>
              </div>
            </div>
          </div>

        </div>

      </div>
    </section>
  );
};

export default ProjectIntro;
