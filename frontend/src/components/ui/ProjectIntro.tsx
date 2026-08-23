import React from 'react';

/**
 * ProjectIntro component representing the core cognitive and infrastructure layers of Moka.
 * Styled with the Black Ice aesthetic: deep obsidian frosted cards, crystalline highlights,
 * and glacial teal accents.
 */
export const ProjectIntro: React.FC = () => {
  return (
    <section id="project-intro" className="w-full bg-transparent py-20 relative overflow-hidden border-y border-white/[0.05]">
      {/* Ambient background glacial glows */}
      <div
        className="absolute -top-40 -left-40 w-96 h-96 rounded-full blur-[140px] pointer-events-none opacity-50"
        style={{ backgroundColor: 'var(--brand-subtle)' }}
      />
      <div
        className="absolute -bottom-40 -right-40 w-96 h-96 rounded-full blur-[140px] pointer-events-none opacity-50"
        style={{ backgroundColor: 'var(--brand-subtle)' }}
      />

      <div className="grid grid-cols-1 md:grid-cols-12 gap-10 max-w-6xl mx-auto px-6 relative z-10 items-center">
        {/* Left Column: Story & Project Overview */}
        <div className="md:col-span-6 flex flex-col items-start">
          <div className="relative inline-block mb-3">
            <h2 className="font-megrim text-4xl md:text-5xl font-bold text-white tracking-wider leading-tight">
              About the Project
            </h2>
            <div className="brand-underline" />
          </div>

          <p className="text-slate-300 text-lg leading-relaxed mt-3">
            <strong style={{ color: 'var(--brand-light)' }} className="font-semibold drop-shadow-[0_0_12px_rgba(0,243,255,0.4)]">
              MoKa
            </strong>{' '}
            transforms Anki Cozmo into an intelligent local AI desktop copilot with genuine physical embodiment.
          </p>
          <p className="text-slate-400 text-sm leading-relaxed mt-3">
            By combining sub-50ms semantic reflex loops with advanced reasoning models, MoKa manages schedules, tracks context, and runs local workspace automation directly from your desk.
          </p>
        </div>

        {/* Right Column: Goal Cards */}
        <div className="md:col-span-6 flex flex-col gap-3.5">
          <div className="group relative theme-card rounded-2xl p-5 hover:-translate-y-0.5 transition-all duration-300">
            <div className="flex items-start gap-4">
              <div className="p-2.5 rounded-xl transition-all duration-300 flex-shrink-0 group-hover:scale-105 theme-icon-box">
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
                </svg>
              </div>
              <div>
                <h4 className="text-white font-semibold text-base transition-colors group-hover:text-[var(--brand-light)]">
                  100% Local Privacy
                </h4>
                <p className="text-slate-400 text-sm mt-1 leading-relaxed">
                  Run all LLMs, computer vision, vector storage, and long-term memory retrieval completely offline to secure personal data.
                </p>
              </div>
            </div>
          </div>

          <div className="group relative theme-card rounded-2xl p-5 hover:-translate-y-0.5 transition-all duration-300">
            <div className="flex items-start gap-4">
              <div className="p-2.5 rounded-xl transition-all duration-300 flex-shrink-0 group-hover:scale-105 theme-icon-box">
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M13 10V3L4 14h7v7l9-11h-7z" />
                </svg>
              </div>
              <div>
                <h4 className="text-white font-semibold text-base transition-colors group-hover:text-[var(--brand-light)]">
                  Dual-Layered Intellect
                </h4>
                <p className="text-slate-400 text-sm mt-1 leading-relaxed">
                  Combine high-speed semantic routers for reflex commands with complex reasoning models for autonomous workflows.
                </p>
              </div>
            </div>
          </div>

          <div className="group relative theme-card rounded-2xl p-5 hover:-translate-y-0.5 transition-all duration-300">
            <div className="flex items-start gap-4">
              <div className="p-2.5 rounded-xl transition-all duration-300 flex-shrink-0 group-hover:scale-105 theme-icon-box">
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z" />
                </svg>
              </div>
              <div>
                <h4 className="text-white font-semibold text-base transition-colors group-hover:text-[var(--brand-light)]">
                  Empathetic Companion Core
                </h4>
                <p className="text-slate-400 text-sm mt-1 leading-relaxed">
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
