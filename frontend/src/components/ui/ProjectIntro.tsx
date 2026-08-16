import React from 'react';

/**
 * ProjectIntro component representing the core cognitive and infrastructure layers of Moka.
 * Styled with dynamic CSS theme variables (var(--brand-primary)) for centralized palette swapping.
 */
export const ProjectIntro: React.FC = () => {
  return (
    <section className="w-full bg-transparent py-20 relative overflow-hidden border-y border-slate-900/80">
      {/* Ambient background glows mapped to theme variable */}
      <div
        className="absolute -top-40 -left-40 w-96 h-96 rounded-full blur-[140px] pointer-events-none"
        style={{ backgroundColor: 'var(--brand-subtle)' }}
      />
      <div
        className="absolute -bottom-40 -right-40 w-96 h-96 rounded-full blur-[140px] pointer-events-none"
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
            <strong style={{ color: 'var(--brand-light)' }} className="font-semibold">
              MoKa
            </strong>{' '}
            transforms Anki Cozmo into an intelligent local AI desktop copilot with genuine physical embodiment.
          </p>
          <p className="text-slate-400 text-sm leading-relaxed mt-3">
            By combining sub-50ms semantic reflex loops with advanced reasoning models, MoKa manages schedules, tracks context, and runs local workspace automation directly from your desk.
          </p>
        </div>

        {/* Right Column: Precision Refined Goal Cards */}
        <div className="md:col-span-6 flex flex-col gap-3.5">
          <div
            className="group relative bg-[#0e1015]/90 border border-slate-800/80 rounded-2xl p-5 hover:-translate-y-0.5 transition-all duration-300"
            style={{
              borderColor: 'var(--border-subtle, #1e293b)'
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.borderColor = 'var(--brand-primary)';
              e.currentTarget.style.boxShadow = '0 8px 30px rgba(0,0,0,0.4), 0 0 24px var(--brand-glow)';
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.borderColor = 'rgba(30, 41, 59, 0.8)';
              e.currentTarget.style.boxShadow = 'none';
            }}
          >
            <div className="flex items-start gap-4">
              <div
                className="p-2.5 rounded-xl transition-all duration-300 flex-shrink-0 group-hover:scale-105"
                style={{
                  backgroundColor: 'var(--brand-subtle)',
                  borderColor: 'var(--brand-border)',
                  borderWidth: '1px',
                  borderStyle: 'solid',
                  color: 'var(--brand-light)'
                }}
              >
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

          <div
            className="group relative bg-[#0e1015]/90 border border-slate-800/80 rounded-2xl p-5 hover:-translate-y-0.5 transition-all duration-300"
            style={{
              borderColor: 'var(--border-subtle, #1e293b)'
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.borderColor = 'var(--brand-primary)';
              e.currentTarget.style.boxShadow = '0 8px 30px rgba(0,0,0,0.4), 0 0 24px var(--brand-glow)';
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.borderColor = 'rgba(30, 41, 59, 0.8)';
              e.currentTarget.style.boxShadow = 'none';
            }}
          >
            <div className="flex items-start gap-4">
              <div
                className="p-2.5 rounded-xl transition-all duration-300 flex-shrink-0 group-hover:scale-105"
                style={{
                  backgroundColor: 'var(--brand-subtle)',
                  borderColor: 'var(--brand-border)',
                  borderWidth: '1px',
                  borderStyle: 'solid',
                  color: 'var(--brand-light)'
                }}
              >
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

          <div
            className="group relative bg-[#0e1015]/90 border border-slate-800/80 rounded-2xl p-5 hover:-translate-y-0.5 transition-all duration-300"
            style={{
              borderColor: 'var(--border-subtle, #1e293b)'
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.borderColor = 'var(--brand-primary)';
              e.currentTarget.style.boxShadow = '0 8px 30px rgba(0,0,0,0.4), 0 0 24px var(--brand-glow)';
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.borderColor = 'rgba(30, 41, 59, 0.8)';
              e.currentTarget.style.boxShadow = 'none';
            }}
          >
            <div className="flex items-start gap-4">
              <div
                className="p-2.5 rounded-xl transition-all duration-300 flex-shrink-0 group-hover:scale-105"
                style={{
                  backgroundColor: 'var(--brand-subtle)',
                  borderColor: 'var(--brand-border)',
                  borderWidth: '1px',
                  borderStyle: 'solid',
                  color: 'var(--brand-light)'
                }}
              >
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
