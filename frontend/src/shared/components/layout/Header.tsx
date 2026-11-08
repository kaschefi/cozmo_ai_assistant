import React from 'react';
import { AnimatedTopDock } from './AnimatedTopDock';
import ThemeSelector from './ThemeSelector';
import { HeaderParticleLogo } from './HeaderParticleLogo';
import '../../shaders/threeui.css';

export interface HeaderProps {
  defaultActive?: string;
  showParticleLogo?: boolean;
}

/**
 * Header component representing the sticky top navigation bar across Moka pages.
 * Houses the interactive HeaderParticleLogo (default for all pages except home),
 * the ThreeUI <AnimatedTopDock /> centered, and the ThemeSelector on the right.
 */
export const Header: React.FC<HeaderProps> = ({ 
  defaultActive = "home",
  showParticleLogo 
}) => {
  // Home page has its own full-page ParticleCanvas, so default to false for home, true for all other pages
  const shouldShowLogo = showParticleLogo ?? (defaultActive !== 'home');

  return (
    <header className="fixed top-0 left-0 w-full h-20 md:h-24 bg-[#03060a]/85 border-b border-white/[0.06] backdrop-blur-2xl z-30 flex items-center justify-between px-6 md:px-10 overflow-visible shadow-[0_4px_30px_rgba(0,0,0,0.85)]">
      {/* Left: Interactive Particle Logo (MOKA <-> Eyes) */}
      <div className="flex items-center z-40 min-w-[120px] sm:min-w-[150px]">
        {shouldShowLogo ? (
          <HeaderParticleLogo />
        ) : (
          <div className="w-10 sm:w-28 hidden sm:block pointer-events-none" />
        )}
      </div>

      {/* Center: ThreeUI AnimatedTopDock - Mathematically centered in viewport */}
      <div className="absolute left-1/2 -translate-x-1/2 flex items-center justify-center pointer-events-none z-30">
        <div className="pointer-events-auto">
          <AnimatedTopDock defaultActive={defaultActive} />
        </div>
      </div>

      {/* Right-aligned Theme Selector */}
      <div className="flex items-center justify-end z-40 min-w-[120px] sm:min-w-[150px]">
        <ThemeSelector />
      </div>
    </header>
  );
};

export default Header;
