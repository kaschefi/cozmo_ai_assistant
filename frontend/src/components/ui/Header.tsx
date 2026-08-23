import React from 'react';
import { AnimatedTopDock } from '../../shaders/animated-top-dock/AnimatedTopDock';
import ThemeSelector from './ThemeSelector';
import '../../shaders/threeui.css';

export interface HeaderProps {
  defaultActive?: string;
}

/**
 * Header component representing the sticky top navigation bar across Moka pages.
 * Houses the ThreeUI <AnimatedTopDock /> centered and the ThemeSelector on the right.
 */
export const Header: React.FC<HeaderProps> = ({ defaultActive = "home" }) => {
  return (
    <header className="fixed top-0 left-0 w-full h-20 md:h-24 bg-[#03060a]/85 border-b border-white/[0.06] backdrop-blur-2xl z-30 flex items-center justify-between px-6 md:px-10 overflow-visible shadow-[0_4px_30px_rgba(0,0,0,0.85)]">
      {/* Invisible balancer on the left so dock stays perfectly centered */}
      <div className="w-10 sm:w-28 hidden sm:block pointer-events-none" />

      {/* Centered Top Dock */}
      <div className="flex-1 flex justify-center items-center">
        <AnimatedTopDock defaultActive={defaultActive} />
      </div>

      {/* Right-aligned Theme Selector */}
      <div className="flex items-center justify-end z-40">
        <ThemeSelector />
      </div>
    </header>
  );
};

export default Header;
