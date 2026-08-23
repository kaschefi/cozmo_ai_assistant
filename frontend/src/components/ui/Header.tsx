import React from 'react';
import { AnimatedTopDock } from '../../shaders/animated-top-dock/AnimatedTopDock';
import '../../shaders/threeui.css';

/**
 * Header component representing the sticky top navigation bar on the Moka Landing page.
 * Houses the ThreeUI <AnimatedTopDock /> placed right in the middle of the header.
 */
export const Header: React.FC = () => {
  return (
    <header className="fixed top-0 left-0 w-full h-20 md:h-24 bg-[#08090c]/85 border-b border-[#1c1e29]/70 backdrop-blur-xl z-30 flex items-center justify-center px-6 overflow-visible">
      <AnimatedTopDock />
    </header>
  );
};


export default Header;
