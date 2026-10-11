import React from 'react';

interface ChatLeftRailProps {
  onNewChat: () => void;
  onToggleHistory: () => void;
  isHistoryOpen: boolean;
  historyCount: number;
}

export const ChatLeftRail: React.FC<ChatLeftRailProps> = ({
  onNewChat,
  onToggleHistory,
  isHistoryOpen,
  historyCount,
}) => {
  return (
    <aside
      id="chat-left-rail"
      aria-label="Chat quick tools"
      className="fixed top-20 md:top-24 bottom-0 left-0 w-14 sm:w-16 z-50 flex flex-col items-center py-4 bg-transparent border-none pointer-events-none transition-all duration-300"
    >
      {/* Top Group: Floating Action Buttons */}
      <div className="flex flex-col items-center gap-3 w-full pointer-events-auto">
        {/* New Chat Button (Gemini-Inspired Edit/Pencil Icon) */}
        <div className="relative group">
          <button
            id="rail-new-chat-btn"
            onClick={onNewChat}
            className="w-10 h-10 rounded-2xl flex items-center justify-center transition-all duration-200 cursor-pointer bg-white/[0.06] hover:bg-[var(--brand-primary)]/15 border border-white/[0.1] hover:border-[var(--brand-primary)]/50 text-slate-200 hover:text-[var(--brand-primary)] hover:shadow-[0_0_16px_var(--brand-glow)] backdrop-blur-md active:scale-95"
            title="New Chat (Ctrl+J)"
            aria-label="New Chat"
          >
            {/* Gemini-style edit / pencil icon */}
            <svg
              className="w-4 h-4 transition-transform duration-200 group-hover:scale-110"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={2}
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M16.862 4.487l1.687-1.688a1.875 1.875 0 112.652 2.652L6.832 19.82a4.5 4.5 0 01-1.897 1.13l-2.685.8.8-2.685a4.5 4.5 0 011.13-1.897L16.863 4.487zm0 0L19.5 7.125"
              />
            </svg>
          </button>
          {/* Tooltip */}
          <div
            className={`absolute left-full ml-3 top-1/2 -translate-y-1/2 px-2.5 py-1 rounded-lg bg-[#0b101b] border border-white/10 text-white text-[11px] font-sans font-medium whitespace-nowrap opacity-0 pointer-events-none transition-opacity shadow-lg z-50 ${
              isHistoryOpen ? '!opacity-0 pointer-events-none' : 'group-hover:opacity-100'
            }`}
          >
            New Chat <span className="text-slate-500 font-mono text-[10px] ml-1">Ctrl+J</span>
          </div>
        </div>

        {/* Chat History Flyout Trigger */}
        <div className="relative group">
          <button
            id="rail-history-toggle-btn"
            onClick={onToggleHistory}
            className={`w-10 h-10 rounded-2xl flex items-center justify-center transition-all duration-200 cursor-pointer border relative backdrop-blur-md active:scale-95 ${
              isHistoryOpen
                ? 'bg-[var(--brand-primary)]/15 border-[var(--brand-primary)] text-[var(--brand-primary)] shadow-[0_0_16px_var(--brand-glow)]'
                : 'bg-white/[0.06] hover:bg-white/[0.1] border-white/[0.1] hover:border-white/25 text-slate-300 hover:text-white'
            }`}
            title="Chat History (Ctrl+H)"
            aria-label="Chat History"
            aria-expanded={isHistoryOpen}
          >
            <svg
              className={`w-4 h-4 transition-transform duration-200 ${
                isHistoryOpen ? 'text-[var(--brand-primary)] scale-110' : 'group-hover:scale-110'
              }`}
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={2}
            >
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 6v6l4 2" />
              <circle cx="12" cy="12" r="9" />
            </svg>

            {/* History Count Badge Dot */}
            {historyCount > 0 && (
              <span className="absolute -top-1 -right-1 flex h-4 min-w-[16px] px-1 items-center justify-center rounded-full bg-[var(--brand-primary)] text-[9px] font-mono font-bold text-black shadow-[0_0_8px_var(--brand-glow)]">
                {historyCount > 99 ? '99+' : historyCount}
              </span>
            )}
          </button>
          {/* Tooltip */}
          <div
            className={`absolute left-full ml-3 top-1/2 -translate-y-1/2 px-2.5 py-1 rounded-lg bg-[#0b101b] border border-white/10 text-white text-[11px] font-sans font-medium whitespace-nowrap opacity-0 pointer-events-none transition-opacity shadow-lg z-50 ${
              isHistoryOpen ? '!opacity-0 pointer-events-none' : 'group-hover:opacity-100'
            }`}
          >
            Chat History <span className="text-slate-500 font-mono text-[10px] ml-1">Ctrl+H</span>
          </div>
        </div>
      </div>
    </aside>
  );
};

export default ChatLeftRail;
