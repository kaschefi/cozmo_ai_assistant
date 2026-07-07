import React from 'react';
import Header from './ui/Header';
import FeatureMarquee from './ui/FeatureMarquee';
import TalkSection from './ui/TalkSection';
import ParticleCanvas from './ui/ParticleCanvas';

/**
 * MokaLanding component representing the main ecosystem dashboard.
 * Abstracted into modular sub-components for enhanced readability, separation of concerns,
 * and component-driven architecture.
 */
export const MokaLanding: React.FC = () => {
  return (
    <div className="relative min-h-[220vh] bg-gradient-to-br from-[#020512] via-[#070b1a] to-[#020512] overflow-x-hidden select-none">
      {/* Subtle digital grid overlay */}
      <div
        className="absolute inset-0 pointer-events-none opacity-[0.03] z-10"
        style={{
          backgroundImage: 'radial-gradient(circle, #00f3ff 1px, transparent 1px)',
          backgroundSize: '30px 30px'
        }}
      />

      {/* Fixed Sticky Header Bar */}
      <Header />

      {/* Fixed canvas on top of everything so particles float over the header and content */}
      <ParticleCanvas />

      {/* Fixed dark vignette overlay to keep contrast high */}
      <div className="fixed inset-0 bg-[radial-gradient(circle_at_center,transparent_20%,rgba(2,5,18,0.85)_100%)] pointer-events-none z-16" />

      {/* Foreground content card that scrolls up */}
      <div className="relative w-full max-w-5xl mx-auto px-6 pt-[105vh] pb-32 z-20 pointer-events-auto">
        {/* Infinite scrolling showcase of Cozmo Agent capabilities */}
        <FeatureMarquee />

        {/* Talk Section with target button and orbiting particles */}
        <TalkSection />
      </div>
    </div>
  );
};

export default MokaLanding;
