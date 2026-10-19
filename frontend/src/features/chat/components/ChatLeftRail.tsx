import React, { useEffect, useRef, useState } from 'react';
import { createVerticalDockController } from '../../../shared/components/layout/verticalDockController';
import robotIcon from '../../../assets/robot.png';

interface ChatLeftRailProps {
  onNewChat: () => void;
  onToggleHistory: () => void;
  isHistoryOpen: boolean;
  historyCount: number;
  isCozmoConnected?: boolean;
  isCozmoConnecting?: boolean;
  cozmoError?: string | null;
  onToggleCozmo?: () => void;
}

export const ChatLeftRail: React.FC<ChatLeftRailProps> = ({
  onNewChat,
  onToggleHistory,
  isHistoryOpen,
  historyCount,
  isCozmoConnected = false,
  isCozmoConnecting = false,
  cozmoError = null,
  onToggleCozmo,
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
      className={`fixed top-20 md:top-24 bottom-0 left-0 w-14 sm:w-16 z-30 flex flex-col items-start py-4 pl-2 sm:pl-3 bg-transparent border-none pointer-events-none transition-all duration-300 ease-out overflow-visible ${
        isHistoryOpen ? 'opacity-0 -translate-x-12 pointer-events-none' : 'opacity-100 translate-x-0'
      }`}
    >
      <nav
        ref={rootRef}
        className={`animated-vertical-dock__nav overflow-visible transition-all duration-200 ${
          isHistoryOpen ? 'pointer-events-none opacity-0' : 'pointer-events-auto opacity-100'
        }`}
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

        {/* Item 3: Cozmo Robot & Voice Listener */}
        <button
          id="rail-cozmo-toggle-btn"
          className={`animated-vertical-dock__item !px-1.5 transition-all duration-300 ${
            isCozmoConnected
              ? '!border-emerald-500/60 !text-emerald-400 !bg-[#111114] shadow-[0_0_18px_rgba(16,185,129,0.25)]'
              : isCozmoConnecting
              ? '!border-amber-500/50 !text-amber-400 !bg-[#111114] animate-pulse'
              : cozmoError
              ? '!border-rose-500/70 !text-rose-400 !bg-[#1b0d13] shadow-[0_0_18px_rgba(244,63,94,0.35)] hover:!border-rose-400'
              : ''
          }`}
          data-dock-item
          type="button"
          aria-pressed={isCozmoConnected}
          onClick={onToggleCozmo}
          title={
            isCozmoConnected
              ? 'Cozmo Connected (Speaker & "Hey Buddy" active) - Click to disconnect'
              : isCozmoConnecting
              ? 'Connecting to Cozmo...'
              : cozmoError
              ? `${cozmoError} - Click to retry`
              : 'Connect to Cozmo (Robot speaker & "Hey Buddy" voice listener)'
          }
          aria-label={
            isCozmoConnected
              ? 'Disconnect Cozmo'
              : isCozmoConnecting
              ? 'Connecting to Cozmo'
              : cozmoError
              ? `Cozmo connection failed: ${cozmoError}. Click to retry.`
              : 'Connect to Cozmo'
          }
        >
          <span className="animated-vertical-dock__icon !w-[26px] !h-[26px] relative flex items-center justify-center shrink-0" aria-hidden="true">
            {isCozmoConnecting ? (
              <svg className="w-[23px] h-[23px] animate-spin text-amber-400" viewBox="0 0 24 24" fill="none">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="2.5" />
                <path className="opacity-90" fill="currentColor" d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z" />
              </svg>
            ) : (
              <span
                className={`w-[23px] h-[23px] transition-all duration-300 ${
                  isCozmoConnected
                    ? 'bg-emerald-400 drop-shadow-[0_0_8px_rgba(52,211,153,0.9)] scale-105'
                    : cozmoError
                    ? 'bg-rose-400 drop-shadow-[0_0_8px_rgba(244,63,94,0.9)] scale-105'
                    : 'bg-slate-300 hover:bg-white hover:scale-110 drop-shadow-[0_0_4px_rgba(255,255,255,0.25)]'
                }`}
                style={{
                  maskImage: `url(${robotIcon})`,
                  WebkitMaskImage: `url(${robotIcon})`,
                  maskSize: 'contain',
                  WebkitMaskSize: 'contain',
                  maskRepeat: 'no-repeat',
                  WebkitMaskRepeat: 'no-repeat',
                  maskPosition: 'center',
                  WebkitMaskPosition: 'center',
                }}
              />
            )}

            {/* Glowing state badge */}
            {isCozmoConnected && (
              <span className="absolute -top-1 -right-1 w-2.5 h-2.5 rounded-full bg-emerald-400 ring-2 ring-emerald-950 shadow-[0_0_10px_rgba(52,211,153,1)]" />
            )}
            {isCozmoConnecting && (
              <span className="absolute -top-1 -right-1 w-2.5 h-2.5 rounded-full bg-amber-400 animate-ping" />
            )}
            {!isCozmoConnecting && !isCozmoConnected && cozmoError && (
              <span className="absolute -top-1.5 -right-1.5 w-3 h-3 rounded-full bg-rose-500 ring-2 ring-rose-950 shadow-[0_0_10px_rgba(244,63,94,1)] flex items-center justify-center text-[9px] font-bold text-white leading-none">
                !
              </span>
            )}
          </span>
          <span className="animated-vertical-dock__label" data-dock-label>
            <span className={cozmoError && !isCozmoConnected && !isCozmoConnecting ? 'text-rose-400 font-semibold tracking-wider' : ''}>
              {isCozmoConnected ? 'COZMO ON' : isCozmoConnecting ? 'CONNECTING...' : cozmoError ? 'RETRY COZMO' : 'COZMO'}
            </span>
          </span>
        </button>
      </nav>
    </aside>
  );
};

export default ChatLeftRail;
