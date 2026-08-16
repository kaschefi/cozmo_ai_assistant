import React from 'react';
import Header from './ui/Header';
import ProjectIntro from './ui/ProjectIntro';
import FeatureMarquee from './ui/FeatureMarquee';
import TalkSection from './ui/TalkSection';
import ParticleCanvas from './ui/ParticleCanvas';

/**
 * MokaLanding component representing the main ecosystem dashboard.
 * Abstracted into modular sub-components for enhanced readability, separation of concerns,
 * and component-driven architecture.
 */
interface MokaLandingProps {
  onStartChat?: () => void;
}

export const MokaLanding: React.FC<MokaLandingProps> = ({ onStartChat }) => {
  return (
    <div className="relative min-h-[220vh] bg-gradient-to-br from-[#08090c] via-[#0e1015] to-[#050608] overflow-x-hidden">
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
      <div className="fixed inset-0 bg-[radial-gradient(circle_at_center,transparent_20%,rgba(8,9,12,0.9)_100%)] pointer-events-none z-16" />

      {/* Foreground content card that scrolls up */}
      <div className="relative w-full pt-[105vh] pb-32 z-20 pointer-events-auto flex flex-col gap-20">
        {/* Technical Architecture Block (Full-screen width bg) */}
        <ProjectIntro />

        {/* Modular elements wrapper (centered layout) */}
        <div className="w-full max-w-5xl mx-auto px-6 flex flex-col gap-20">
          {/* Infinite scrolling showcase of Cozmo Agent capabilities */}
          <FeatureMarquee />

          {/* Talk Section with target button and orbiting particles */}
          <TalkSection onStartChat={onStartChat} />
        </div>
      </div>
    </div>
  );
};

export default MokaLanding;
