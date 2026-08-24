import React from 'react';
import Header from './ui/Header';
import ProjectIntro from './ui/ProjectIntro';
import FeatureMarquee from './ui/FeatureMarquee';
import TalkSection from './ui/TalkSection';
import ParticleCanvas from './ui/ParticleCanvas';
import GoldVeinsBackground from './ui/GoldVeinsBackground';
import ParticleDriftBackground from './ui/ParticleDriftBackground';
import ConstellationFieldBackground from './ui/ConstellationFieldBackground';
import CozmoSection from './ui/CozmoSection';
import { useTheme } from '../context/ThemeContext';

/**
 * MokaLanding component representing the main ecosystem dashboard.
 * Supports:
 * - Clean Obsidian "Default" theme
 * - ThreeUI Constellation Field (Interface Lines) "Black Ice" theme
 * - Liquid Kintsugi 24k Gold Veins "Royal" theme
 * - ThreeUI "Particle Drift" ASCII Cyber Green & Black IT theme
 */
interface MokaLandingProps {
  onStartChat?: () => void;
  onNavigateToCozmo?: () => void;
}

export const MokaLanding: React.FC<MokaLandingProps> = ({ onStartChat, onNavigateToCozmo }) => {
  const { theme } = useTheme();
  const isBlackIce = theme === 'black-ice';
  const isRoyal = theme === 'royal';
  const isIT = theme === 'it';

  return (
    <div className={`relative min-h-[220vh] ${
      isBlackIce ? 'bg-[#020407]' : isRoyal ? 'bg-[#030407]' : isIT ? 'bg-[#020503]' : 'bg-[#030407]'
    } overflow-x-hidden transition-colors duration-700`}>
      {/* Dynamic Background Layer */}
      <div 
        className="fixed inset-0 pointer-events-none z-0 transition-opacity duration-700"
        style={{
          background: isBlackIce
            ? `
              radial-gradient(ellipse 90% 60% at 70% 30%, rgba(0, 243, 255, 0.12) 0%, rgba(8, 60, 77, 0.22) 35%, transparent 75%),
              radial-gradient(ellipse 60% 80% at 20% 80%, rgba(0, 243, 255, 0.06) 0%, rgba(6, 30, 42, 0.3) 40%, transparent 80%),
              linear-gradient(135deg, #020407 0%, #03080e 25%, #05141f 55%, #082836 85%, #061c27 100%)
            `
            : isRoyal
            ? `
              radial-gradient(ellipse 80% 60% at 75% 25%, rgba(212, 175, 55, 0.08) 0%, rgba(30, 25, 15, 0.25) 40%, transparent 75%),
              radial-gradient(ellipse 60% 70% at 25% 75%, rgba(255, 215, 0, 0.05) 0%, rgba(18, 16, 12, 0.3) 45%, transparent 80%),
              linear-gradient(135deg, #030407 0%, #06070b 30%, #0a0c12 65%, #020305 100%)
            `
            : isIT
            ? 'linear-gradient(180deg, #020503 0%, #030805 50%, #010402 100%)'
            : 'linear-gradient(180deg, #030407 0%, #05060a 50%, #020305 100%)'
        }}
      />

      {/* 🌌 ThreeUI Constellation Field (Interface Lines) Background (Rendered for Black Ice) */}
      {isBlackIce && (
        <ConstellationFieldBackground className="fixed inset-0 pointer-events-none z-0" />
      )}

      {/* 👑 Liquid Kintsugi 24k Gold Veins Background (Rendered for Royal) */}
      {isRoyal && (
        <GoldVeinsBackground className="fixed inset-0 pointer-events-none z-0" />
      )}

      {/* 💻 ThreeUI Particle Drift ASCII Cyber Data Stream (Rendered for IT) */}
      {isIT && (
        <ParticleDriftBackground className="fixed inset-0 pointer-events-none z-0" />
      )}

      {/* 👑 Floating Sub-surface Royal Gold & Warm Amber Lights (Rendered ONLY for Royal) */}
      {isRoyal && (
        <>
          <div 
            className="fixed top-1/4 right-[12%] w-[520px] h-[520px] rounded-full blur-[160px] pointer-events-none z-[2] opacity-30 animate-pulse"
            style={{ backgroundColor: 'rgba(212, 175, 55, 0.12)', animationDuration: '7s' }}
          />
          <div 
            className="fixed bottom-1/4 left-[8%] w-[480px] h-[480px] rounded-full blur-[150px] pointer-events-none z-[2] opacity-20"
            style={{ backgroundColor: 'rgba(255, 215, 0, 0.08)' }}
          />
        </>
      )}

      {/* Subtle digital grid overlay */}
      <div
        className="fixed inset-0 pointer-events-none opacity-[0.035] z-[3]"
        style={{
          backgroundImage: isBlackIce 
            ? 'radial-gradient(circle, #00f3ff 1px, transparent 1px)' 
            : isRoyal
            ? 'radial-gradient(circle, rgba(212, 175, 55, 0.6) 1px, transparent 1px)'
            : isIT
            ? 'radial-gradient(circle, rgba(0, 255, 102, 0.6) 1px, transparent 1px)'
            : 'radial-gradient(circle, rgba(255, 255, 255, 0.4) 1px, transparent 1px)',
          backgroundSize: '28px 28px'
        }}
      />

      {/* Fixed Sticky Header Bar with Theme Switcher */}
      <Header />

      {/* Fixed canvas on top so glowing particles float effortlessly over the Black Ice backdrop */}
      <ParticleCanvas />

      {/* Fixed dark obsidian vignette overlay for deep contrast & focus */}
      <div 
        className="fixed inset-0 pointer-events-none z-16"
        style={{
          background: 'radial-gradient(circle at 50% 45%, transparent 25%, rgba(2, 4, 7, 0.6) 75%, rgba(2, 4, 7, 0.95) 100%)'
        }}
      />

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

          {/* Cozmo Robotics Embodiment Section & Dashboard Invitation */}
          <CozmoSection onNavigateToCozmo={onNavigateToCozmo} />
        </div>
      </div>
    </div>
  );
};

export default MokaLanding;
