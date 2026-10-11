import React, { useEffect, useRef, useState } from 'react';
import { createVerticalDockController } from './verticalDockController';

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
  const rootRef = useRef<HTMLElement>(null);
  const [justClickedNewChat, setJustClickedNewChat] = useState(false);

  useEffect(() => {
    const root = rootRef.current;
    if (!root) return undefined;
    return createVerticalDockController(root);
  }, []);

  const handleNewChatClick = () => {
    setJustClickedNewChat(true);
    onNewChat();
    setTimeout(() => {
      setJustClickedNewChat(false);
    }, 280);
  };

  return (
    <aside
      id="chat-left-rail"
      aria-label="Chat quick tools"
      className="fixed top-20 md:top-24 bottom-0 left-0 w-14 sm:w-16 z-50 flex flex-col items-start py-4 pl-2 sm:pl-3 bg-transparent border-none pointer-events-none transition-all duration-300 overflow-visible"
    >
      <nav
        ref={rootRef}
        className="animated-vertical-dock__nav pointer-events-auto overflow-visible"
        aria-label="Vertical navigation dock"
        data-dock-state="idle"
      >
        {/* Item 1: New Chat */}
        <button
          id="rail-new-chat-btn"
          className="animated-vertical-dock__item"
          data-dock-item
          type="button"
          aria-pressed={justClickedNewChat}
          onClick={handleNewChatClick}
          title="New Chat"
          aria-label="New Chat"
        >
          <span className="animated-vertical-dock__icon" aria-hidden="true">
            <svg viewBox="0 0 24 24">
              <path d="M16.862 4.487l1.687-1.688a1.875 1.875 0 112.652 2.652L6.832 19.82a4.5 4.5 0 01-1.897 1.13l-2.685.8.8-2.685a4.5 4.5 0 011.13-1.897L16.863 4.487zm0 0L19.5 7.125" />
            </svg>
          </span>
          <span className="animated-vertical-dock__label" data-dock-label>
            <span>NEW CHAT</span>
          </span>
        </button>

        {/* Item 2: Chat History */}
        <button
          id="rail-history-toggle-btn"
          className="animated-vertical-dock__item"
          data-dock-item
          type="button"
          aria-pressed={isHistoryOpen}
          onClick={onToggleHistory}
          title="Chat History"
          aria-label="Chat History"
        >
          <span className="animated-vertical-dock__icon relative" aria-hidden="true">
            <svg viewBox="0 0 24 24">
              <path d="M12 6v6l4 2" />
              <circle cx="12" cy="12" r="9" />
            </svg>
            {historyCount > 0 && (
              <span className="absolute -top-0.5 -right-0.5 w-1.5 h-1.5 rounded-full bg-slate-400" />
            )}
          </span>
          <span className="animated-vertical-dock__label" data-dock-label>
            <span>HISTORY</span>
          </span>
        </button>
      </nav>
    </aside>
  );
};

export default ChatLeftRail;
