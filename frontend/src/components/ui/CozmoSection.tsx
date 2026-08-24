import React from 'react';
import CozmoModelPreview from './CozmoModelPreview';

interface CozmoSectionProps {
  onNavigateToCozmo?: () => void;
}

export const CozmoSection: React.FC<CozmoSectionProps> = ({ onNavigateToCozmo }) => {
  const handleLaunchDashboard = () => {
    if (onNavigateToCozmo) {
      onNavigateToCozmo();
    } else {
      window.history.pushState({}, '', '/cozmo');
      window.dispatchEvent(new Event('popstate'));
    }
  };

  return (
    <section
      id="cozmo-section"
      className="w-full py-20 border-t border-white/[0.05] relative z-20 scroll-mt-28"
    >
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 lg:gap-12 items-center w-full">
        {/* Left Column: Focused Narrative & High-Impact CTA */}
        <div className="lg:col-span-6 flex flex-col items-start gap-6">
          <div className="relative inline-block">
            <h2 id="cozmo-title" className="font-megrim text-4xl md:text-5xl text-white tracking-wider leading-tight">
              MoKa <span className="text-[var(--brand-light)] font-sans font-light">×</span> Cozmo
            </h2>
            <div className="brand-underline mt-1" />
          </div>

          <div className="flex flex-col gap-3 max-w-xl text-slate-300 font-sans">
            <p className="text-base sm:text-lg leading-relaxed text-slate-200 font-medium">
              Cozmo is MoKa&apos;s physical body—giving your AI assistant tangible presence and eyes in the real world.
            </p>
            <p className="text-sm sm:text-base leading-relaxed text-slate-400">
              See what Cozmo sees in real-time video, navigate its interactive 3D spatial map, teach custom landmarks, and command motor kinematics across your desk.
            </p>
          </div>

          {/* Call to Action Button */}
          <div className="pt-2 flex flex-col sm:flex-row items-start sm:items-center gap-4 w-full sm:w-auto">
            <button
              id="launch-cozmo-dashboard-btn"
              onClick={handleLaunchDashboard}
              className="w-full sm:w-auto px-8 py-4 rounded-2xl theme-btn text-white font-bold tracking-wide flex items-center justify-center gap-3 cursor-pointer group shadow-[0_10px_30px_rgba(0,0,0,0.5)] hover:scale-[1.02] transition-all duration-300"
            >
              <div className="w-8 h-8 rounded-xl theme-icon-box flex items-center justify-center group-hover:scale-110 transition-transform duration-300">
                <svg className="w-4 h-4 text-current" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                  <path strokeLinecap="round" strokeLinejoin="round" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                </svg>
              </div>
              <span className="text-sm sm:text-base font-semibold text-slate-100 group-hover:text-[var(--brand-light)] transition-colors">
                See What Cozmo Sees
              </span>
              <svg
                className="w-4 h-4 ml-1 text-slate-400 group-hover:text-white group-hover:translate-x-1.5 transition-all duration-300"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                strokeWidth={2.2}
              >
                <path strokeLinecap="round" strokeLinejoin="round" d="M14 5l7 7m0 0l-7 7m7-7H3" />
              </svg>
            </button>
          </div>
        </div>

        {/* Right Column: Interactive 3D Cozmo Model Viewport */}
        <div className="lg:col-span-6 w-full flex flex-col items-center justify-center">
          <CozmoModelPreview />
        </div>
      </div>
    </section>
  );
};

export default CozmoSection;
