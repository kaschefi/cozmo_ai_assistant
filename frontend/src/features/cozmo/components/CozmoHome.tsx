import React from 'react';
import { useCozmoEyeTracking } from '../hooks/useCozmoEyeTracking';

/**
 * CozmoHome component represents the visual layout for the home page.
 * It implements three structural layers:
 * 1. Screen Canvas & Gradient Background with a digital matrix dot overlay (z-0).
 * 2. Layer A (The Face Plate): Standalone centered eyes layer (z-10) with sharp, wide-set Cozmo eyes.
 * 3. Layer B (The Text Content Card): Sits on top in the foreground (z-20) as a glassmorphism card.
 */
export const CozmoHome: React.FC = () => {
  // Call custom eye tracking hook for looking logic
  const { offsetX, offsetY } = useCozmoEyeTracking(16);

  return (
    <div 
      className="relative w-screen h-screen bg-gradient-to-br from-[#020617] via-[#0a1128] to-[#020617] overflow-hidden flex flex-col justify-center items-center"
      data-testid="cozmo-home"
    >
      {/* 1. SCREEN CANVAS: Subtle digital matrix grid overlay (Cyan dots, 5% opacity) */}
      <div 
        className="absolute inset-0 pointer-events-none opacity-5 z-0"
        style={{
          backgroundImage: 'radial-gradient(circle, #00f3ff 1.2px, transparent 1.2px)',
          backgroundSize: '24px 24px'
        }}
      />

      {/* 2. LAYER A: THE FACE PLATE (Background Layer, z-10) */}
      <div className="absolute inset-0 flex items-center justify-center pointer-events-none z-10">
        {/* Subtle dark vignette overlay around the eyes to keep text crisp */}
        <div className="absolute inset-0 bg-radial from-transparent via-slate-950/20 to-slate-950/60 pointer-events-none z-11" />

        {/* Wide-set Cozmo Eyes (centered, z-12) */}
        <div className="flex justify-between w-[90vw] max-w-[48rem] px-4 md:px-0">
          {/* Left Eye */}
          <div 
            className="w-24 h-24 md:w-28 md:h-28 rounded-[2rem] bg-[#00f3ff] animate-eye-blink transition-transform duration-75 ease-out"
            style={{ 
              transform: `translate(${offsetX}px, ${offsetY}px)`,
              filter: 'drop-shadow(0 0 20px rgba(0, 243, 255, 0.6))'
            }}
          />
          {/* Right Eye */}
          <div 
            className="w-24 h-24 md:w-28 md:h-28 rounded-[2rem] bg-[#00f3ff] animate-eye-blink transition-transform duration-75 ease-out"
            style={{ 
              transform: `translate(${offsetX}px, ${offsetY}px)`,
              filter: 'drop-shadow(0 0 20px rgba(0, 243, 255, 0.6))'
            }}
          />
        </div>
      </div>

      {/* 3. LAYER B: FOREGROUND NAVIGATION & HERO LAYER (z-20) */}
      
      {/* Top Header Bar */}
      <header className="absolute top-0 left-0 w-full flex justify-between items-center px-6 py-6 md:px-12 md:py-8 z-20">
        {/* MOKA brand logo with cyan glow */}
        <div className="text-xl md:text-2xl font-black tracking-widest text-[#00f3ff] drop-shadow-[0_0_8px_rgba(0,243,255,0.5)] font-sans">
          MOKA
        </div>

        {/* Connected state indicator */}
        <div className="flex items-center gap-2 text-xs md:text-sm text-slate-400 font-medium tracking-wide">
          <span className="w-2 h-2 rounded-full bg-emerald-500 shadow-[0_0_8px_#10b981] animate-pulse" />
          Core Brain: Connected
        </div>
      </header>

      {/* Central Hero Card */}
      <main className="w-[90%] max-w-[30rem] mx-auto rounded-2xl bg-black/20 border border-slate-800/80 backdrop-blur-md p-8 md:p-12 shadow-[0_20px_50px_rgba(0,0,0,0.5)] text-center relative z-20">
        {/* Main Title */}
        <h1 className="text-2xl md:text-4xl font-extrabold tracking-tight text-white mb-4 leading-tight">
          I am MOKA.<br />Your Agentic Assistant.
        </h1>

        {/* Subtitle */}
        <p className="text-slate-300 text-sm md:text-base mb-8 leading-relaxed font-normal">
          A multi-agent intelligence pipeline balancing local automation with stateful human verification.
        </p>

        {/* Sleek CTA Button */}
        <button 
          type="button"
          className="px-8 py-3 rounded-lg bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-white font-semibold tracking-wide shadow-[0_0_20px_rgba(0,243,255,0.3)] transition-all duration-300 hover:scale-[1.02] hover:shadow-[0_0_25px_rgba(0,243,255,0.5)] active:scale-95 cursor-pointer"
        >
          Launch Control Panel
        </button>
      </main>
    </div>
  );
};

export default CozmoHome;
