import React, { useState, useRef, useEffect } from 'react';
import { useTheme, type ThemeId } from '../../context/ThemeContext';

export const ThemeSelector: React.FC = () => {
  const { theme, setTheme, themes } = useTheme();
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Close dropdown on outside click
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setIsOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const currentTheme = themes.find((t) => t.id === theme) || themes[0];

  return (
    <div className="relative" ref={dropdownRef}>
      {/* Floating Pill Trigger */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-2.5 px-3 py-1.5 rounded-full bg-[#08080c]/80 border border-white/[0.08] hover:border-white/[0.18] shadow-[0_4px_16px_rgba(0,0,0,0.5)] backdrop-blur-xl transition-all duration-300 group cursor-pointer"
        title="Change Visual Theme"
        aria-label="Theme Selector"
      >
        {/* Theme Indicator */}
        <div className={`w-5 h-5 rounded-full flex items-center justify-center flex-shrink-0 ${
          theme === 'black-ice' 
            ? 'bg-gradient-to-tr from-[#083c4d] to-[#00f3ff] shadow-[0_0_8px_rgba(0,243,255,0.5)]' 
            : theme === 'royal'
            ? 'bg-gradient-to-tr from-[#0f3b25] to-[#d4af37] shadow-[0_0_8px_rgba(212,175,55,0.6)]'
            : theme === 'it'
            ? 'bg-gradient-to-tr from-[#052e16] to-[#12a574] shadow-[0_0_8px_rgba(18,165,116,0.6)]'
            : 'bg-zinc-800 border border-white/20'
        }`}>
          {theme === 'black-ice' ? (
            <svg className="w-3 h-3 text-slate-950 font-bold" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 3v18m0-18l3 3m-3-3l-3 3m0 12l3 3m0 0l3-3m-6-6h18m-18 0l3-3m-3 3l3 3m12-6l3 3m0 0l-3 3" />
            </svg>
          ) : theme === 'royal' ? (
            <svg className="w-3 h-3 text-slate-950 font-bold" fill="currentColor" viewBox="0 0 24 24">
              <path d="M5 16L3 5l5.5 5L12 4l3.5 6L21 5l-2 11H5zm14 3c0 .6-.4 1-1 1H6c-.6 0-1-.4-1-1v-1h14v1z" />
            </svg>
          ) : theme === 'it' ? (
            <svg className="w-3 h-3 text-slate-950 font-bold" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M8 9l3 3-3 3m5 0h3M5 20h14a2 2 0 002-2V6a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
            </svg>
          ) : (
            <svg className="w-3 h-3 text-zinc-300 font-bold" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M7 21a4 4 0 01-4-4V5a2 2 0 012-2h4a2 2 0 012 2v12a4 4 0 01-4 4zm0 0h12a2 2 0 002-2v-4a2 2 0 00-2-2h-2.343M11 7.343l1.657-1.657a2 2 0 012.828 0l2.829 2.829a2 2 0 010 2.828l-8.486 8.485M7 17h.01" />
            </svg>
          )}
        </div>

        <span className="text-xs font-semibold text-slate-200 group-hover:text-white transition-colors tracking-wide hidden sm:inline">
          {currentTheme.name}
        </span>

        {/* Small chevron */}
        <svg
          className={`w-3.5 h-3.5 text-slate-400 group-hover:text-white transition-transform duration-300 ${
            isOpen ? 'rotate-180' : ''
          }`}
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          strokeWidth={2}
        >
          <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {/* Dropdown Menu */}
      {isOpen && (
        <div className="absolute right-0 mt-2 w-64 p-2 rounded-2xl bg-[#08080c]/95 border border-white/[0.1] backdrop-blur-2xl shadow-[0_20px_50px_rgba(0,0,0,0.85)] z-50 flex flex-col gap-1.5 animate-in fade-in zoom-in-95 duration-200">
          <div className="px-3 py-1.5 text-[10px] font-mono uppercase tracking-wider text-slate-400 border-b border-white/[0.06] flex items-center justify-between">
            <span>Theme Presets</span>
            <span
              className="font-semibold transition-colors duration-300"
              style={{
                color: theme === 'royal' ? '#d4af37' : theme === 'it' ? '#12a574' : '#00f3ff'
              }}
            >
              Particles: {theme === 'royal' ? 'Gold' : theme === 'it' ? 'Phthalo Green' : 'Cyan'}
            </span>
          </div>

          {themes.map((t) => {
            const isSelected = t.id === theme;
            return (
              <button
                key={t.id}
                onClick={() => {
                  setTheme(t.id as ThemeId);
                  setIsOpen(false);
                }}
                className={`w-full p-2.5 rounded-xl flex items-center gap-3 text-left transition-all duration-200 group cursor-pointer ${
                  isSelected
                    ? 'bg-white/[0.06] border border-white/[0.15] shadow-[0_0_12px_rgba(255,255,255,0.05)]'
                    : 'hover:bg-white/[0.03] border border-transparent'
                }`}
              >
                {/* 4-Color Swatch Preview */}
                <div className="flex -space-x-1.5 overflow-hidden rounded-full p-0.5 border border-slate-700/60 bg-slate-950 flex-shrink-0">
                  {t.previewColors.map((c, i) => (
                    <div
                      key={i}
                      className="w-3.5 h-3.5 rounded-full"
                      style={{ backgroundColor: c }}
                    />
                  ))}
                </div>

                <div className="flex flex-col flex-1 min-w-0">
                  <div className="flex items-center justify-between">
                    <span
                      className={`text-xs font-bold tracking-wide ${
                        isSelected ? 'text-white' : 'text-slate-300 group-hover:text-white'
                      }`}
                    >
                      {t.name}
                    </span>
                    {isSelected && (
                      <span 
                        className="w-1.5 h-1.5 rounded-full" 
                        style={{
                          backgroundColor: t.id === 'royal' ? '#d4af37' : t.id === 'it' ? '#12a574' : '#00f3ff',
                          boxShadow: t.id === 'royal' ? '0 0 6px #d4af37' : t.id === 'it' ? '0 0 6px #12a574' : '0 0 6px #00f3ff'
                        }}
                      />
                    )}
                  </div>
                  <span className="text-[10px] text-slate-400 truncate mt-0.5">
                    {t.description}
                  </span>
                </div>
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
};

export default ThemeSelector;
