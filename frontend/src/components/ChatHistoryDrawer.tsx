import React, { useState, useMemo, useEffect, useRef } from 'react';
import {
  type ChatSession,
  formatSessionTime
} from '../lib/chatHistory';

interface ChatHistoryDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  sessions: ChatSession[];
  activeSessionId: string;
  onSelectSession: (session: ChatSession) => void;
  onNewChat: () => void;
  onDeleteSession: (sessionId: string) => void;
  onRenameSession: (sessionId: string, newTitle: string) => void;
  onClearAll: () => void;
  onSyncLangSmith?: () => Promise<void>;
  isSyncingLangSmith?: boolean;
  syncNotice?: string | null;
}

export const ChatHistoryDrawer: React.FC<ChatHistoryDrawerProps> = ({
  isOpen,
  onClose,
  sessions,
  activeSessionId,
  onSelectSession,
  onNewChat,
  onDeleteSession,
  onRenameSession,
  onClearAll,
  onSyncLangSmith,
  isSyncingLangSmith,
  syncNotice,
}) => {
  const [searchQuery, setSearchQuery] = useState('');
  const [editingSessionId, setEditingSessionId] = useState<string | null>(null);
  const [editTitleText, setEditTitleText] = useState('');
  const [showClearConfirm, setShowClearConfirm] = useState(false);
  const editInputRef = useRef<HTMLInputElement | null>(null);

  // Close on Escape key press
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isOpen) {
        if (editingSessionId) {
          setEditingSessionId(null);
        } else if (showClearConfirm) {
          setShowClearConfirm(false);
        } else {
          onClose();
        }
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, editingSessionId, showClearConfirm, onClose]);

  // Focus rename input when activated
  useEffect(() => {
    if (editingSessionId) {
      editInputRef.current?.focus();
      editInputRef.current?.select();
    }
  }, [editingSessionId]);

  const handleStartRename = (e: React.MouseEvent, session: ChatSession) => {
    e.stopPropagation();
    setEditingSessionId(session.id);
    setEditTitleText(session.title);
  };

  const handleSaveRename = (sessionId: string) => {
    const cleanTitle = editTitleText.trim();
    if (cleanTitle) {
      onRenameSession(sessionId, cleanTitle);
    }
    setEditingSessionId(null);
  };

  const handleKeyDownRename = (e: React.KeyboardEvent, sessionId: string) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      handleSaveRename(sessionId);
    } else if (e.key === 'Escape') {
      setEditingSessionId(null);
    }
  };

  // Filter sessions by search query
  const filteredSessions = useMemo(() => {
    if (!searchQuery.trim()) return sessions;
    const q = searchQuery.toLowerCase();
    return sessions.filter(session => {
      const matchTitle = session.title.toLowerCase().includes(q);
      const matchMessage = session.messages.some(m => m.text.toLowerCase().includes(q));
      return matchTitle || matchMessage;
    });
  }, [sessions, searchQuery]);

  // Group sessions by date
  const groupedSessions = useMemo(() => {
    const now = new Date();
    const startOfToday = new Date(now.getFullYear(), now.getMonth(), now.getDate()).getTime();
    const startOfYesterday = startOfToday - 86400000;
    const startOfWeek = startOfToday - 6 * 86400000;

    const groups: { [key: string]: ChatSession[] } = {
      Today: [],
      Yesterday: [],
      'Previous 7 Days': [],
      Older: []
    };

    filteredSessions.forEach(session => {
      const t = session.updatedAt || session.createdAt;
      if (t >= startOfToday) {
        groups['Today'].push(session);
      } else if (t >= startOfYesterday) {
        groups['Yesterday'].push(session);
      } else if (t >= startOfWeek) {
        groups['Previous 7 Days'].push(session);
      } else {
        groups['Older'].push(session);
      }
    });

    return Object.entries(groups).filter(([_, items]) => items.length > 0);
  }, [filteredSessions]);

  return (
    <>
      {/* Backdrop overlay */}
      <div
        className={`fixed inset-0 bg-black/65 backdrop-blur-sm z-40 transition-opacity duration-300 ${
          isOpen ? 'opacity-100 pointer-events-auto' : 'opacity-0 pointer-events-none'
        }`}
        onClick={onClose}
        aria-hidden="true"
      />

      {/* Slide-out Drawer Panel */}
      <aside
        id="chat-history-sidebar"
        className={`fixed top-0 left-0 h-full w-[330px] sm:w-[380px] max-w-[85vw] z-50 flex flex-col bg-[#03060c]/95 border-r border-white/[0.08] backdrop-blur-2xl shadow-[0_0_50px_rgba(0,0,0,0.85)] transition-transform duration-300 ease-out ${
          isOpen ? 'translate-x-0' : '-translate-x-full'
        }`}
        aria-label="Chat history sidebar"
        aria-hidden={!isOpen}
      >
        {/* Top Header Bar */}
        <div className="flex items-center justify-between px-5 pt-5 pb-4 border-b border-white/[0.06]">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-xl bg-[var(--brand-primary)]/10 border border-[var(--brand-primary)]/20 flex items-center justify-center text-[var(--brand-primary)] shadow-[0_0_12px_var(--brand-glow)]">
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 6v6l4 2" />
                <circle cx="12" cy="12" r="9" />
              </svg>
            </div>
            <div>
              <h2 className="text-sm font-semibold text-white tracking-wide flex items-center gap-2">
                Chat History
                <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-white/[0.06] border border-white/[0.08] text-slate-400 font-normal">
                  {sessions.length}
                </span>
              </h2>
            </div>
          </div>

          <button
            onClick={onClose}
            className="w-8 h-8 rounded-xl bg-white/[0.04] hover:bg-white/[0.08] border border-white/[0.08] hover:border-white/20 text-slate-400 hover:text-white flex items-center justify-center transition-all cursor-pointer"
            title="Close history"
            aria-label="Close history"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Action: New Chat & LangSmith Sync Buttons */}
        <div className="p-4 pb-2 flex flex-col gap-2">
          <button
            onClick={() => {
              onNewChat();
              onClose();
            }}
            className="w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-2xl bg-[var(--brand-primary)]/15 hover:bg-[var(--brand-primary)]/25 border border-[var(--brand-primary)]/35 text-[var(--brand-primary)] hover:text-white font-medium text-xs tracking-wide transition-all duration-200 cursor-pointer shadow-[0_0_20px_var(--brand-glow)] group"
          >
            <svg
              className="w-4 h-4 transition-transform duration-300 group-hover:rotate-90 text-[var(--brand-primary)]"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={2.5}
            >
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
            </svg>
            <span>New Conversation</span>
          </button>

          {onSyncLangSmith && (
            <button
              onClick={onSyncLangSmith}
              disabled={isSyncingLangSmith}
              className="w-full flex items-center justify-center gap-2 px-3 py-1.5 rounded-xl bg-white/[0.04] hover:bg-white/[0.08] border border-white/[0.08] hover:border-cyan-500/30 text-slate-300 hover:text-cyan-300 font-medium text-[11px] tracking-wide transition-all cursor-pointer disabled:opacity-50 group"
              title="Restore previous conversations from LangSmith project traces"
            >
              <svg
                className={`w-3.5 h-3.5 text-cyan-400 ${isSyncingLangSmith ? 'animate-spin' : 'group-hover:scale-110 transition-transform'}`}
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                strokeWidth={2}
              >
                <path strokeLinecap="round" strokeLinejoin="round" d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0l3.181 3.183a8.25 8.25 0 0013.803-3.7M4.031 9.865a8.25 8.25 0 0113.803-3.7l3.181 3.182m0-4.991v4.99" />
              </svg>
              <span>{isSyncingLangSmith ? 'Syncing from LangSmith...' : 'Sync from LangSmith'}</span>
            </button>
          )}

          {syncNotice && (
            <div className="text-[10px] text-cyan-300 font-mono text-center bg-cyan-950/40 border border-cyan-800/50 py-1 px-2 rounded-lg">
              {syncNotice}
            </div>
          )}
        </div>

        {/* Search Bar */}
        {sessions.length > 0 && (
          <div className="px-4 py-2">
            <div className="relative w-full">
              <svg
                className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                strokeWidth={2}
              >
                <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-5.197-5.197m0 0A7.5 7.5 0 105.196 5.196a7.5 7.5 0 0010.607 10.607z" />
              </svg>
              <input
                type="text"
                value={searchQuery}
                onChange={e => setSearchQuery(e.target.value)}
                placeholder="Search history..."
                className="w-full pl-8 pr-7 py-2 bg-white/[0.04] border border-white/[0.08] focus:border-[var(--brand-primary)]/50 focus:bg-white/[0.06] rounded-xl text-xs text-white placeholder-slate-500 outline-none transition-all"
              />
              {searchQuery && (
                <button
                  onClick={() => setSearchQuery('')}
                  className="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-500 hover:text-white p-0.5"
                  title="Clear search"
                >
                  <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              )}
            </div>
          </div>
        )}

        {/* Scrollable Conversation List */}
        <div className="flex-1 overflow-y-auto px-4 py-2 space-y-4">
          {sessions.length === 0 ? (
            <div className="h-full flex flex-col items-center justify-center text-center p-6 text-slate-500">
              <div className="w-12 h-12 rounded-2xl bg-white/[0.03] border border-white/[0.06] flex items-center justify-center mb-3 text-slate-500">
                <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M7.5 8.25h9m-9 3H12m-9.75 1.51c0 1.6 1.123 2.994 2.707 3.227 1.129.166 2.27.293 3.423.379.35.026.67.21.865.501L12 21l2.755-4.133a1.14 1.14 0 01.865-.501 48.172 48.172 0 003.423-.379c1.584-.233 2.707-1.626 2.707-3.228V6.741c0-1.602-1.123-2.995-2.707-3.228A48.394 48.394 0 0012 3c-2.392 0-4.744.175-7.043.513C3.373 3.746 2.25 5.14 2.25 6.741v6.27z" />
                </svg>
              </div>
              <p className="text-xs font-medium text-slate-400">No chat history yet</p>
              <p className="text-[11px] text-slate-600 mt-1">Your conversations with MoKa will be saved here automatically.</p>
            </div>
          ) : filteredSessions.length === 0 ? (
            <div className="py-12 text-center text-slate-500 text-xs">
              No conversations found matching &ldquo;{searchQuery}&rdquo;
            </div>
          ) : (
            groupedSessions.map(([groupName, groupItems]) => (
              <div key={groupName} className="space-y-1.5">
                <div className="text-[10px] font-mono uppercase tracking-wider text-slate-500 px-2 py-1 font-semibold">
                  {groupName}
                </div>
                {groupItems.map(session => {
                  const isActive = session.id === activeSessionId;
                  const isEditing = session.id === editingSessionId;
                  const messageCount = session.messages.length;
                  const lastMessage = session.messages[session.messages.length - 1];

                  return (
                    <div
                      key={session.id}
                      onClick={() => {
                        if (!isEditing) {
                          onSelectSession(session);
                          onClose();
                        }
                      }}
                      className={`group relative p-3 rounded-xl border transition-all duration-200 cursor-pointer flex flex-col gap-1.5 ${
                        isActive
                          ? 'bg-[var(--brand-primary)]/10 border-[var(--brand-primary)]/40 shadow-[0_0_16px_var(--brand-glow)]'
                          : 'bg-white/[0.02] hover:bg-white/[0.06] border-white/[0.05] hover:border-white/15'
                      }`}
                    >
                      {/* Top row: Title and Actions */}
                      <div className="flex items-center justify-between gap-2">
                        {isEditing ? (
                          <div
                            className="flex-1 flex items-center gap-1.5"
                            onClick={e => e.stopPropagation()}
                          >
                            <input
                              ref={editInputRef}
                              type="text"
                              value={editTitleText}
                              onChange={e => setEditTitleText(e.target.value)}
                              onKeyDown={e => handleKeyDownRename(e, session.id)}
                              onBlur={() => handleSaveRename(session.id)}
                              className="w-full bg-black/60 border border-[var(--brand-primary)] rounded-lg px-2 py-0.5 text-xs text-white outline-none"
                            />
                            <button
                              onClick={() => handleSaveRename(session.id)}
                              className="p-1 text-[var(--brand-primary)] hover:text-white cursor-pointer"
                              title="Save"
                            >
                              <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                                <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
                              </svg>
                            </button>
                          </div>
                        ) : (
                          <>
                            <div className="flex items-center gap-2 min-w-0 flex-1">
                              {isActive && (
                                <span className="w-1.5 h-1.5 rounded-full bg-[var(--brand-primary)] shadow-[0_0_6px_var(--brand-primary)] flex-shrink-0" />
                              )}
                              <span
                                className={`text-xs font-medium truncate ${
                                  isActive ? 'text-white font-semibold' : 'text-slate-300 group-hover:text-white'
                                }`}
                                title={session.title}
                              >
                                {session.title}
                              </span>
                            </div>

                            {/* Action Buttons (Rename, Delete) */}
                            <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                              <button
                                onClick={e => handleStartRename(e, session)}
                                className="p-1 rounded-md text-slate-500 hover:text-white hover:bg-white/[0.08] transition-colors cursor-pointer"
                                title="Rename title"
                                aria-label="Rename title"
                              >
                                <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                                  <path strokeLinecap="round" strokeLinejoin="round" d="M16.862 4.487l1.687-1.688a1.875 1.875 0 112.652 2.652L6.832 19.82a4.5 4.5 0 01-1.897 1.13l-2.685.8.8-2.685a4.5 4.5 0 011.13-1.897L16.863 4.487zm0 0L19.5 7.125" />
                                </svg>
                              </button>
                              <button
                                onClick={e => {
                                  e.stopPropagation();
                                  onDeleteSession(session.id);
                                }}
                                className="p-1 rounded-md text-slate-500 hover:text-rose-400 hover:bg-rose-500/10 transition-colors cursor-pointer"
                                title="Delete conversation"
                                aria-label="Delete conversation"
                              >
                                <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                                  <path strokeLinecap="round" strokeLinejoin="round" d="M14.74 9l-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 01-2.244 2.077H8.084a2.25 2.25 0 01-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 00-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 013.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 00-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 00-7.5 0" />
                                </svg>
                              </button>
                            </div>
                          </>
                        )}
                      </div>

                      {/* Bottom row: Preview snippet & relative timestamp */}
                      <div className="flex items-center justify-between text-[10px] text-slate-500">
                        <span className="truncate max-w-[180px]">
                          {lastMessage ? (
                            lastMessage.sender === 'user' ? `You: ${lastMessage.text}` : `MoKa: ${lastMessage.text}`
                          ) : (
                            `${messageCount} messages`
                          )}
                        </span>
                        <span className="font-mono text-slate-500 whitespace-nowrap">
                          {formatSessionTime(session.updatedAt || session.createdAt)}
                        </span>
                      </div>
                    </div>
                  );
                })}
              </div>
            ))
          )}
        </div>

        {/* Bottom Bar: Clear All or Info */}
        {sessions.length > 0 && (
          <div className="p-4 border-t border-white/[0.06] bg-black/40">
            {showClearConfirm ? (
              <div className="flex flex-col gap-2">
                <p className="text-[11px] text-rose-300 font-medium">Delete all saved conversations?</p>
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => {
                      onClearAll();
                      setShowClearConfirm(false);
                    }}
                    className="flex-1 py-1.5 rounded-lg bg-rose-600/30 hover:bg-rose-600/50 border border-rose-500/40 text-rose-200 text-xs font-semibold cursor-pointer transition-all"
                  >
                    Yes, Clear All
                  </button>
                  <button
                    onClick={() => setShowClearConfirm(false)}
                    className="px-3 py-1.5 rounded-lg bg-white/[0.06] hover:bg-white/[0.1] text-slate-300 text-xs cursor-pointer transition-all"
                  >
                    Cancel
                  </button>
                </div>
              </div>
            ) : (
              <div className="flex items-center justify-between">
                <div className="flex flex-col">
                  <span className="text-[10px] text-slate-400 font-mono">
                    {sessions.length} {sessions.length === 1 ? 'chat' : 'chats'} in database
                  </span>
                  <span className="text-[9px] text-slate-500 font-sans">
                    Auto-deleted after 30 days
                  </span>
                </div>
                <button
                  onClick={() => setShowClearConfirm(true)}
                  className="text-[11px] text-slate-500 hover:text-rose-400 transition-colors flex items-center gap-1 cursor-pointer"
                  title="Clear all conversations"
                >
                  <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M14.74 9l-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 01-2.244 2.077H8.084a2.25 2.25 0 01-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 00-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 013.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 00-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 00-7.5 0" />
                  </svg>
                  Clear All
                </button>
              </div>
            )}
          </div>
        )}
      </aside>
    </>
  );
};

export default ChatHistoryDrawer;
