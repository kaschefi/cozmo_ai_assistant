import React from 'react';

/**
 * Header component representing the sticky top navigation bar on the Moka Landing page.
 * Leaves visual space on the left for the floating particle MOKA logo and displays
 * the active Core Brain connection status on the right.
 */
export const Header: React.FC = () => {
  return (
    <header className="fixed top-0 left-0 w-full h-24 bg-[#020512]/90 border-b border-slate-900/60 backdrop-blur-md z-30 flex items-center justify-between px-12">
      {/* Left side spacer to let MOKA particle logo float in the header */}
      <div className="w-40" />

      {/* Right side connection state indicator */}
      <div className="flex items-center gap-2 text-xs md:text-sm text-slate-400 font-medium tracking-wide">
        <span className="w-2 h-2 rounded-full bg-emerald-500 shadow-[0_0_8px_#10b981] animate-pulse" />
        Core Brain: Connected
      </div>
    </header>
  );
};

export default Header;
