import React from 'react';

/**
 * Header component representing the sticky top navigation bar on the Moka Landing page.
 * Leaves visual space on the left for the floating particle MOKA logo and displays
 * the active Core Brain connection status on the right.
 */
export const Header: React.FC = () => {
  return (
    <header className="fixed top-0 left-0 w-full h-24 bg-[#08090c]/90 border-b border-[#1c1e29]/70 backdrop-blur-md z-30 flex items-center justify-between px-12">
      {/* Left side spacer to let MOKA particle logo float in the header */}
      <div className="w-40" />

      {/* Right side connection state indicator */}
      <a
        href="/chat"
        onClick={(e) => {
          e.preventDefault();
          window.history.pushState({}, '', '/chat');
          window.dispatchEvent(new Event('popstate'));
        }}
        className="relative group px-5 py-2.5 rounded-xl bg-slate-950/80 border border-cyan-500/60 hover:border-cyan-400 text-cyan-400 font-bold text-xs md:text-sm tracking-wide shadow-[0_0_20px_rgba(0,243,255,0.25)] hover:shadow-[0_0_35px_rgba(0,243,255,0.5)] transition-all duration-300 hover:scale-105 active:scale-95 flex items-center gap-2.5 cursor-pointer overflow-hidden focus-visible:ring-2 focus-visible:ring-cyan-400"
        aria-label="Open Chat Page"
      >
        <div className="flex items-end gap-0.5 h-3.5" aria-hidden="true">
          <span className="w-0.5 h-3 bg-cyan-400 rounded-full animate-bounce [animation-delay:0ms]" />
          <span className="w-0.5 h-3.5 bg-cyan-400 rounded-full animate-bounce [animation-delay:150ms]" />
          <span className="w-0.5 h-2.5 bg-cyan-400 rounded-full animate-bounce [animation-delay:300ms]" />
        </div>
        <span className="text-cyan-400 font-bold">Open Chat</span>
      </a>
    </header>
  );
};

export default Header;
