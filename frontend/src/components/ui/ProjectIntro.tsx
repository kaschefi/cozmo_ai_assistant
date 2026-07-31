import React from 'react';

/**
 * ProjectIntro component representing the core cognitive and infrastructure layers of Moka.
 * Sits directly below the hero section and features marquee.
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
            <h2 className="text-3xl md:text-4xl font-bold text-white tracking-tight leading-tight">
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
          <h3 className="text-xl font-semibold text-slate-200 tracking-wide uppercase text-sm border-b border-slate-800 pb-2">
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

      {/* ========================================================================= */}
      {/* COMMENTED OUT: ORIGINAL TECHNICAL ARCHITECTURE SECTION                    */}
      {/* ========================================================================= */}
      {false && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-12 max-w-6xl mx-auto px-6 relative z-10 items-center">

          {/* Left Column: Core Copy & Definition */}
          <div className="flex flex-col justify-center items-start">
            <div className="relative inline-block mb-6">
              <h2 className="text-3xl md:text-4xl font-bold text-white tracking-tight leading-tight">
                Technical Architecture
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
            <p className="text-slate-400 text-lg leading-relaxed mt-2">
              Moka is a <span className="text-white font-medium">local, privacy-focused agentic system</span> running via <span className="text-white font-medium">Ollama</span>. It is powered by a sophisticated <span className="text-white font-medium">dual-layer memory architecture</span>, combining short-term checkpoint tracking with long-term RAG vector lookups.
            </p>
            <p className="text-slate-400 text-lg leading-relaxed mt-4">
              Designed for low-latency physical interactions and secure tool execution, Moka balances cognitive autonomy with absolute user control through built-in <span className="text-[#00d2ff] font-medium">human-in-the-loop safety gates</span>.
            </p>
          </div>

          {/* Right Column: Visual Tech Stack Component */}
          <div className="flex flex-col items-stretch justify-center relative">

            {/* Stack Block 1 - Perception */}
            <div className="relative group">
              <div className="flex items-center gap-4 bg-slate-900/35 border border-slate-800/80 rounded-2xl p-5 backdrop-blur-md hover:bg-slate-900/60 hover:border-[#00d2ff]/40 hover:shadow-[0_0_25px_rgba(0,210,255,0.08)] transition-all duration-300">
                <div className="p-3 bg-slate-950/80 rounded-xl border border-slate-800/85 group-hover:border-[#00d2ff]/30 transition-colors">
                  <svg className="w-6 h-6 text-[#00d2ff]" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z" />
                  </svg>
                </div>
                <div className="flex-1">
                  <h3 className="text-white font-semibold text-base md:text-lg tracking-tight group-hover:text-[#00d2ff] transition-colors">
                    Perception & UI
                  </h3>
                  <p className="text-slate-400 text-sm mt-0.5">
                    Web Frontend / Voice Interface
                  </p>
                </div>
                <div className="text-[10px] uppercase font-bold text-slate-500 tracking-wider bg-slate-950/60 px-2.5 py-1 rounded-md border border-slate-800/80">
                  Layer 1
                </div>
              </div>
            </div>

            {/* Flow Connector 1 */}
            <div className="flex flex-col items-center my-1 select-none pointer-events-none">
              <div className="w-[2px] h-6 bg-gradient-to-b from-[#00d2ff]/40 to-[#00d2ff]/10 relative">
                <div className="absolute w-1.5 h-1.5 bg-cyan-300 rounded-full -left-[2px] animate-flow-dot shadow-[0_0_6px_#00d2ff]" />
              </div>
              <div className="w-0 h-0 border-l-[3px] border-l-transparent border-r-[3px] border-r-transparent border-t-[5px] border-t-[#00d2ff]/60" />
            </div>

            {/* Stack Block 2 - Cognition */}
            <div className="relative group">
              <div className="flex items-center gap-4 bg-slate-900/35 border border-slate-800/80 rounded-2xl p-5 backdrop-blur-md hover:bg-slate-900/60 hover:border-[#00d2ff]/40 hover:shadow-[0_0_25px_rgba(0,210,255,0.08)] transition-all duration-300">
                <div className="p-3 bg-slate-950/80 rounded-xl border border-slate-800/85 group-hover:border-[#00d2ff]/30 transition-colors">
                  <svg className="w-6 h-6 text-[#00d2ff]" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M18 10a6 6 0 00-12 0v8a6 6 0 0012 0v-8zm-6 4h.01M9 16h6" />
                  </svg>
                </div>
                <div className="flex-1">
                  <h3 className="text-white font-semibold text-base md:text-lg tracking-tight group-hover:text-[#00d2ff] transition-colors">
                    Cognition & Flow
                  </h3>
                  <p className="text-slate-400 text-sm mt-0.5">
                    LangGraph Agentic Orchestrator
                  </p>
                </div>
                <div className="text-[10px] uppercase font-bold text-slate-500 tracking-wider bg-slate-950/60 px-2.5 py-1 rounded-md border border-slate-800/80">
                  Layer 2
                </div>
              </div>
            </div>

            {/* Flow Connector 2 */}
            <div className="flex flex-col items-center my-1 select-none pointer-events-none">
              <div className="w-[2px] h-6 bg-gradient-to-b from-[#00d2ff]/40 to-[#00d2ff]/10 relative">
                <div className="absolute w-1.5 h-1.5 bg-cyan-300 rounded-full -left-[2px] animate-flow-dot shadow-[0_0_6px_#00d2ff] [animation-delay:0.75s]" />
              </div>
              <div className="w-0 h-0 border-l-[3px] border-l-transparent border-r-[3px] border-r-transparent border-t-[5px] border-t-[#00d2ff]/60" />
            </div>

            {/* Stack Block 3 - Memory */}
            <div className="relative group">
              <div className="flex items-center gap-4 bg-slate-900/35 border border-slate-800/80 rounded-2xl p-5 backdrop-blur-md hover:bg-slate-900/60 hover:border-[#00d2ff]/40 hover:shadow-[0_0_25px_rgba(0,210,255,0.08)] transition-all duration-300">
                <div className="p-3 bg-slate-950/80 rounded-xl border border-slate-800/85 group-hover:border-[#00d2ff]/30 transition-colors">
                  <svg className="w-6 h-6 text-[#00d2ff]" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
                  </svg>
                </div>
                <div className="flex-1">
                  <h3 className="text-white font-semibold text-base md:text-lg tracking-tight group-hover:text-[#00d2ff] transition-colors">
                    Memory Fabric
                  </h3>
                  <p className="text-slate-400 text-sm mt-0.5">
                    Short-Term State + Long-Term Vector RAG
                  </p>
                </div>
                <div className="text-[10px] uppercase font-bold text-slate-500 tracking-wider bg-slate-950/60 px-2.5 py-1 rounded-md border border-slate-800/80">
                  Layer 3
                </div>
              </div>
            </div>

            {/* Flow Connector 3 */}
            <div className="flex flex-col items-center my-1 select-none pointer-events-none">
              <div className="w-[2px] h-6 bg-gradient-to-b from-[#00d2ff]/40 to-[#00d2ff]/10 relative">
                <div className="absolute w-1.5 h-1.5 bg-cyan-300 rounded-full -left-[2px] animate-flow-dot shadow-[0_0_6px_#00d2ff] [animation-delay:1.5s]" />
              </div>
              <div className="w-0 h-0 border-l-[3px] border-l-transparent border-r-[3px] border-r-transparent border-t-[5px] border-t-[#00d2ff]/60" />
            </div>

            {/* Stack Block 4 - Local Infra */}
            <div className="relative group">
              <div className="flex items-center gap-4 bg-slate-900/35 border border-slate-800/80 rounded-2xl p-5 backdrop-blur-md hover:bg-slate-900/60 hover:border-[#00d2ff]/40 hover:shadow-[0_0_25px_rgba(0,210,255,0.08)] transition-all duration-300">
                <div className="p-3 bg-slate-950/80 rounded-xl border border-slate-800/85 group-hover:border-[#00d2ff]/30 transition-colors">
                  <svg className="w-6 h-6 text-[#00d2ff]" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M5 12h14M5 12a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v4a2 2 0 01-2 2M5 12a2 2 0 00-2 2v4a2 2 0 002 2h14a2 2 0 002-2v-4a2 2 0 00-2-2m-2-4h.01M17 16h.01" />
                  </svg>
                </div>
                <div className="flex-1">
                  <h3 className="text-white font-semibold text-base md:text-lg tracking-tight group-hover:text-[#00d2ff] transition-colors">
                    Local Infrastructure
                  </h3>
                  <p className="text-slate-400 text-sm mt-0.5">
                    Ollama Engine: Qwen / Gemma
                  </p>
                </div>
                <div className="text-[10px] uppercase font-bold text-slate-500 tracking-wider bg-slate-950/60 px-2.5 py-1 rounded-md border border-slate-800/80">
                  Layer 4
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </section>
  );
};

export default ProjectIntro;
