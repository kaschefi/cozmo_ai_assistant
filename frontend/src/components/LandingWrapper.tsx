import React, { useEffect, useState } from 'react';
import { useMouseTracking } from '../hooks/useMouseTracking';

/**
 * LandingWrapper component provides a full-viewport background with a dark gradient.
 * Inspired by Cozmo's hardware colors (slate and deep navy/indigo).
 * Captures mouse movement coordinates via the useMouseTracking hook.
 * Renders an interactive, responsive face plate with glowing eyes that track the cursor.
 */
export const LandingWrapper: React.FC = () => {
  const { x, y } = useMouseTracking();
  const [windowSize, setWindowSize] = useState({ width: 1200, height: 800 });

  useEffect(() => {
    if (typeof window !== 'undefined') {
      setWindowSize({ width: window.innerWidth, height: window.innerHeight });
      const handleResize = () => {
        setWindowSize({ width: window.innerWidth, height: window.innerHeight });
      };
      window.addEventListener('resize', handleResize);
      return () => window.removeEventListener('resize', handleResize);
    }
  }, []);

  // Compute center coordinates
  const centerX = windowSize.width / 2;
  const centerY = windowSize.height / 2;

  // Calculate mouse delta from viewport center
  const dx = x - centerX;
  const dy = y - centerY;

  // Constrain maximum translation offset (in pixels)
  const maxDistance = Math.min(centerX, centerY) || 1;
  const maxOffset = 16;

  // Compute final translations with smooth look-around vector
  const distance = Math.sqrt(dx * dx + dy * dy);
  const ratio = Math.min(distance / maxDistance, 1);
  const angle = Math.atan2(dy, dx);

  const offsetX = Math.cos(angle) * ratio * maxOffset;
  const offsetY = Math.sin(angle) * ratio * maxOffset;

  return (
    <div
      className="relative w-screen h-screen bg-gradient-to-br from-[#020617] via-[#0a1128] to-[#020617] overflow-hidden flex flex-col justify-center items-center"
      data-testid="landing-wrapper"
      data-mouse-x={x}
      data-mouse-y={y}
    >
      {/* Subtle digital matrix grid overlay (Cyan dots, 5% opacity) */}
      <div
        className="absolute inset-0 pointer-events-none opacity-5"
        style={{
          backgroundImage: 'radial-gradient(circle, #00f3ff 1.2px, transparent 1.2px)',
          backgroundSize: '24px 24px'
        }}
      />

      {/* Center Piece Face Plate Container */}
      <div
        className="relative w-[90vw] h-[22.5vw] md:w-[42rem] md:h-[10.5rem] bg-black/40 border border-slate-800/50 backdrop-blur-md rounded-[2.5vw] md:rounded-3xl shadow-[0_0_60px_rgba(8,51,68,0.3),0_0_30px_rgba(0,243,255,0.15)] flex justify-center items-center transition-all duration-300"
      >
        {/* Interactive Eye Container */}
        <div
          className="flex justify-center items-center gap-[6.4vw] md:gap-12 px-6 md:px-12 w-full h-full"
          style={{
            transform: `translate(${offsetX}px, ${offsetY}px)`,
            transition: 'transform 0.1s ease-out',
          }}
        >
          {/* Left Eye */}
          <div
            className="w-[12.8vw] h-[12.8vw] md:w-24 md:h-24 rounded-[4.2vw] md:rounded-[2rem] bg-gradient-to-b from-[#e6ffff] via-[#33f7ff] to-[#00f3ff] shadow-[0_0_30px_rgba(0,243,255,0.6),inset_0_0_15px_rgba(255,255,255,0.8)] border border-cyan-200/20 animate-eye-blink"
          />

          {/* Right Eye */}
          <div
            className="w-[12.8vw] h-[12.8vw] md:w-24 md:h-24 rounded-[4.2vw] md:rounded-[2rem] bg-gradient-to-b from-[#e6ffff] via-[#33f7ff] to-[#00f3ff] shadow-[0_0_30px_rgba(0,243,255,0.6),inset_0_0_15px_rgba(255,255,255,0.8)] border border-cyan-200/20 animate-eye-blink"
          />
        </div>
      </div>
    </div>
  );
};

export default LandingWrapper;

