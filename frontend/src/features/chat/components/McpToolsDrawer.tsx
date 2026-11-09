import React, { useState, useMemo, useEffect, useRef } from 'react';

export interface McpToolItem {
  name: string;
  description: string;
  is_mutating?: boolean;
}

export interface McpActiveServer {
  pack_id: string;
  display_name: string;
  description: string;
  tools_count: number;
  tools: McpToolItem[];
  tool_names?: string[];
  connected_at?: number;
}

export interface McpDormantServer {
  pack_id: string;
  display_name: string;
  description: string;
  command?: string;
  env_vars?: string[];
}

export interface McpStatusTelemetry {
  active_servers: Record<string, McpActiveServer>;
  dormant_servers: Record<string, McpDormantServer>;
  total_active_servers: number;
  total_dormant_servers: number;
  total_indexed_tools: number;
}

interface McpToolsDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  telemetry: McpStatusTelemetry | null;
  isLoading?: boolean;
  onRefresh?: () => Promise<void>;
  onDisconnectServer?: (packId: string) => Promise<void>;
  onConnectServer?: (packId: string) => Promise<void>;
}

export const McpToolsDrawer: React.FC<McpToolsDrawerProps> = ({
  isOpen,
  onClose,
  telemetry,
  isLoading = false,
  onRefresh,
  onDisconnectServer,
  onConnectServer,
}) => {
  const [searchQuery, setSearchQuery] = useState('');
  const [confirmDisconnectId, setConfirmDisconnectId] = useState<string | null>(null);
  const [actionInProgressId, setActionInProgressId] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const searchInputRef = useRef<HTMLInputElement | null>(null);

  // Close on Escape key press
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isOpen) {
        if (confirmDisconnectId) {
          setConfirmDisconnectId(null);
        } else {
          onClose();
        }
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, confirmDisconnectId, onClose]);

  // Reset confirmation state when drawer closes
  useEffect(() => {
    if (!isOpen) {
      setConfirmDisconnectId(null);
      setActionError(null);
      setSearchQuery('');
    }
  }, [isOpen]);

  const activeServersList = useMemo(() => {
    if (!telemetry?.active_servers) return [];
    return Object.values(telemetry.active_servers);
  }, [telemetry]);

  const dormantServersList = useMemo(() => {
    if (!telemetry?.dormant_servers) return [];
    return Object.values(telemetry.dormant_servers);
  }, [telemetry]);

  // Filter lists by search query
  const filteredActiveServers = useMemo(() => {
    if (!searchQuery.trim()) return activeServersList;
    const q = searchQuery.toLowerCase();
    return activeServersList.filter(s => {
      const matchServer = s.display_name.toLowerCase().includes(q) ||
        s.description.toLowerCase().includes(q) ||
        s.pack_id.toLowerCase().includes(q);
      const matchTool = s.tools?.some(t =>
        t.name.toLowerCase().includes(q) || (t.description && t.description.toLowerCase().includes(q))
      );
      return matchServer || matchTool;
    });
  }, [activeServersList, searchQuery]);

  const filteredDormantServers = useMemo(() => {
    if (!searchQuery.trim()) return dormantServersList;
    const q = searchQuery.toLowerCase();
    return dormantServersList.filter(s =>
      s.display_name.toLowerCase().includes(q) ||
      s.description.toLowerCase().includes(q) ||
      s.pack_id.toLowerCase().includes(q)
    );
  }, [dormantServersList, searchQuery]);

  const handleDisconnect = async (packId: string) => {
    if (!onDisconnectServer) return;
    setActionInProgressId(packId);
    setActionError(null);
    try {
      await onDisconnectServer(packId);
      setConfirmDisconnectId(null);
    } catch (err: any) {
      setActionError(err?.message || `Failed to disconnect ${packId}`);
    } finally {
      setActionInProgressId(null);
    }
  };

  const handleConnect = async (packId: string) => {
    if (!onConnectServer) return;
    setActionInProgressId(packId);
    setActionError(null);
    try {
      await onConnectServer(packId);
    } catch (err: any) {
      setActionError(err?.message || `Failed to connect ${packId}`);
    } finally {
      setActionInProgressId(null);
    }
  };

  return (
    <>
      {/* Backdrop overlay */}
      <div
        className={`fixed inset-0 bg-black/60 backdrop-blur-sm z-40 transition-opacity duration-300 ${isOpen ? 'opacity-100 pointer-events-auto' : 'opacity-0 pointer-events-none'
          }`}
        onClick={onClose}
        aria-hidden="true"
      />

      {/* Flyout Drawer Panel: Clean Frosted Glass */}
      <aside
        id="mcp-tools-sidebar"
        className={`fixed top-0 bottom-0 left-0 h-full w-[360px] sm:w-[440px] max-w-[90vw] z-50 flex flex-col bg-[#03060a]/95 border-r border-white/[0.08] backdrop-blur-2xl shadow-[24px_0_50px_rgba(0,0,0,0.7)] transition-transform duration-300 ease-out select-none ${isOpen ? 'translate-x-0' : '-translate-x-full'
          }`}
        aria-label="MCP Tools Manager"
        aria-hidden={!isOpen}
      >
        {/* Top Header Bar */}
        <div className="flex items-center justify-between px-5 pt-5 pb-4 border-b border-white/[0.06]">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-xl bg-white/[0.04] border border-white/[0.08] flex items-center justify-center text-slate-300">
              <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.8}>
                <rect x="3" y="4" width="18" height="6" rx="2" strokeWidth={1.8} />
                <rect x="3" y="14" width="18" height="6" rx="2" strokeWidth={1.8} />
                <path strokeLinecap="round" strokeLinejoin="round" d="M7 7h.01M7 17h.01M17 7h.01M17 17h.01" strokeWidth={2.5} />
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 10v4" strokeWidth={1.8} />
              </svg>
            </div>
            <div>
              <h2 className="text-xs font-semibold text-white tracking-widest uppercase font-mono flex items-center gap-2">
                MCP Tools
                <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-white/[0.05] border border-white/[0.08] text-slate-300 font-normal">
                  {activeServersList.length} ACTIVE
                </span>
              </h2>
            </div>
          </div>

          <div className="flex items-center gap-1.5">
            {onRefresh && (
              <button
                onClick={onRefresh}
                disabled={isLoading}
                className="w-8 h-8 rounded-xl bg-white/[0.04] hover:bg-white/[0.08] border border-white/[0.08] hover:border-white/20 text-slate-400 hover:text-white flex items-center justify-center transition-all cursor-pointer active:scale-95 disabled:opacity-40"
                title="Refresh MCP telemetry"
                aria-label="Refresh MCP telemetry"
              >
                <svg
                  className={`w-3.5 h-3.5 text-slate-400 ${isLoading ? 'animate-spin text-white' : 'hover:text-white'}`}
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                  strokeWidth={2}
                >
                  <path strokeLinecap="round" strokeLinejoin="round" d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0l3.181 3.183a8.25 8.25 0 0013.803-3.7M4.031 9.865a8.25 8.25 0 0113.803-3.7l3.181 3.182m0-4.991v4.99" />
                </svg>
              </button>
            )}

            <button
              onClick={onClose}
              className="w-8 h-8 rounded-xl bg-white/[0.04] hover:bg-white/[0.08] border border-white/[0.08] hover:border-white/20 text-slate-400 hover:text-white flex items-center justify-center transition-all cursor-pointer active:scale-95"
              title="Close panel"
              aria-label="Close panel"
            >
              <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        </div>

        {/* Global Action Error Banner */}
        {actionError && (
          <div className="mx-4 mt-3 p-2.5 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs font-mono flex items-center justify-between">
            <span>{actionError}</span>
            <button
              onClick={() => setActionError(null)}
              className="text-rose-400 hover:text-white ml-2 text-sm font-bold cursor-pointer"
            >
              &times;
            </button>
          </div>
        )}

        {/* Search Bar */}
        <div className="px-4 py-3">
          <div className="relative w-full">
            <svg
              className="w-3.5 h-3.5 text-slate-500 absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={1.8}
            >
              <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-5.197-5.197m0 0A7.5 7.5 0 105.196 5.196a7.5 7.5 0 0010.607 10.607z" />
            </svg>
            <input
              ref={searchInputRef}
              type="text"
              value={searchQuery}
              onChange={e => setSearchQuery(e.target.value)}
              placeholder="Search tools, servers, capabilities..."
              className="w-full pl-8 pr-7 py-2 bg-white/[0.03] hover:bg-white/[0.05] border border-white/[0.08] focus:border-white/25 focus:bg-white/[0.06] rounded-xl text-xs text-white placeholder-slate-500 font-sans outline-none transition-all"
            />
            {searchQuery && (
              <button
                onClick={() => setSearchQuery('')}
                className="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-500 hover:text-white p-0.5 cursor-pointer"
                title="Clear search"
              >
                <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            )}
          </div>
        </div>

        {/* Scrollable Content Container */}
        <div className="flex-1 overflow-y-auto px-4 py-2 space-y-6">

          {/* Section 1: Active MCP Servers & Tools */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-[10px] font-mono uppercase tracking-widest text-slate-500 px-1 py-0.5 font-semibold flex items-center gap-2">
                <span className="w-1.5 h-1.5 rounded-full bg-white shadow-[0_0_6px_rgba(255,255,255,0.7)]" />
                Active MCP Tool Packs ({filteredActiveServers.length})
              </span>
            </div>

            {filteredActiveServers.length === 0 ? (
              <div className="p-4 rounded-xl bg-white/[0.02] border border-white/[0.06] text-center space-y-2">
                <div className="w-9 h-9 mx-auto rounded-xl bg-white/[0.03] border border-white/[0.08] flex items-center justify-center text-slate-500">
                  <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4" />
                  </svg>
                </div>
                <p className="text-xs text-slate-300 font-medium font-sans">No Active MCP Tools</p>
                <p className="text-[11px] text-slate-500 leading-relaxed font-sans max-w-xs mx-auto">
                  Tools are discovered and dynamically added when requested in chat (after your approval), or you can connect an available tool pack below.
                </p>
              </div>
            ) : (
              <div className="space-y-3">
                {filteredActiveServers.map(server => {
                  const isDisconnecting = actionInProgressId === server.pack_id;
                  const isConfirming = confirmDisconnectId === server.pack_id;

                  return (
                    <div
                      key={server.pack_id}
                      className="p-3.5 rounded-xl bg-white/[0.02] hover:bg-white/[0.04] border border-white/[0.06] hover:border-white/12 transition-all space-y-3 shadow-[0_4px_20px_rgba(0,0,0,0.3)]"
                    >
                      {/* Server Card Header */}
                      <div className="flex items-start justify-between gap-2">
                        <div className="min-w-0 flex-1">
                          <div className="flex items-center gap-2 flex-wrap">
                            <h3 className="text-xs font-semibold text-white tracking-wide font-mono truncate">
                              {server.display_name}
                            </h3>
                            <span className="text-[9px] font-mono px-2 py-0.5 rounded-full bg-white/[0.05] border border-white/[0.08] text-slate-300 font-medium">
                              CONNECTED
                            </span>
                          </div>
                          <p className="text-[11px] text-slate-400 mt-1 leading-snug font-sans">
                            {server.description}
                          </p>
                        </div>

                        {/* Disconnect Button / Confirmation */}
                        <div className="shrink-0 flex items-center gap-1.5">
                          {isConfirming ? (
                            <div className="flex items-center gap-1 animate-in fade-in duration-200">
                              <button
                                onClick={() => handleDisconnect(server.pack_id)}
                                disabled={isDisconnecting}
                                className="px-2.5 py-1 rounded-lg bg-rose-600/30 hover:bg-rose-600/50 border border-rose-500/40 text-rose-200 text-[10px] font-mono font-semibold transition-all cursor-pointer active:scale-95 disabled:opacity-50"
                              >
                                {isDisconnecting ? 'Removing...' : 'Confirm'}
                              </button>
                              <button
                                onClick={() => setConfirmDisconnectId(null)}
                                className="px-2 py-1 rounded-lg bg-white/[0.06] hover:bg-white/[0.1] text-slate-300 text-[10px] font-mono transition-all cursor-pointer"
                              >
                                Cancel
                              </button>
                            </div>
                          ) : (
                            <button
                              onClick={() => setConfirmDisconnectId(server.pack_id)}
                              className="px-2.5 py-1 rounded-lg bg-white/[0.04] hover:bg-white/[0.08] border border-white/[0.08] hover:border-rose-500/30 text-slate-400 hover:text-rose-300 text-[10px] font-mono transition-all cursor-pointer active:scale-95 flex items-center gap-1"
                              title="Disconnect this server and retire its tools from the AI index"
                            >
                              <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                                <path strokeLinecap="round" strokeLinejoin="round" d="M18.364 18.364A9 9 0 005.636 5.636m12.728 12.728A9 9 0 015.636 5.636m12.728 12.728L5.636 5.636" />
                              </svg>
                              Disconnect
                            </button>
                          )}
                        </div>
                      </div>

                      {/* Granular Tools List */}
                      {server.tools && server.tools.length > 0 && (
                        <div className="pt-2.5 border-t border-white/[0.05] space-y-2">
                          <div className="text-[10px] font-mono text-slate-500 uppercase tracking-widest">
                            Available Tools ({server.tools.length})
                          </div>
                          <div className="space-y-1.5 max-h-48 overflow-y-auto pr-1">
                            {server.tools.map(tool => (
                              <div
                                key={tool.name}
                                className="p-2.5 rounded-lg bg-white/[0.02] border border-white/[0.04] hover:bg-white/[0.05] transition-all space-y-1"
                              >
                                <div className="flex items-center justify-between gap-2">
                                  <span className="text-[11px] font-mono font-medium text-white truncate">
                                    {tool.name}
                                  </span>
                                  {tool.is_mutating ? (
                                    <span className="text-[9px] font-mono px-1.5 py-0.5 rounded bg-white/[0.08] border border-white/[0.14] text-white font-medium shrink-0">
                                      MUTATING
                                    </span>
                                  ) : (
                                    <span className="text-[9px] font-mono px-1.5 py-0.5 rounded bg-white/[0.03] border border-white/[0.06] text-slate-400 shrink-0">
                                      READ-ONLY
                                    </span>
                                  )}
                                </div>
                                {tool.description && (
                                  <p className="text-[10px] text-slate-400 font-sans leading-tight">
                                    {tool.description}
                                  </p>
                                )}
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          {/* Section 2: Dormant Capabilities / Catalog */}
          <div className="space-y-3 pt-2">
            <div className="flex items-center justify-between">
              <span className="text-[10px] font-mono uppercase tracking-widest text-slate-500 px-1 py-0.5 font-semibold flex items-center gap-2">
                <span className="w-1.5 h-1.5 rounded-full bg-white/40" />
                Available Capabilities ({filteredDormantServers.length})
              </span>
            </div>

            <p className="text-[11px] text-slate-500 font-sans leading-snug px-1">
              These servers are indexed in MoKa's dormant catalog. When you ask a related query, MoKa will ask for your approval to connect them. You can also connect them manually here.
            </p>

            <div className="space-y-2.5">
              {filteredDormantServers.map(server => {
                const isConnecting = actionInProgressId === server.pack_id;

                return (
                  <div
                    key={server.pack_id}
                    className="p-3 rounded-xl bg-white/[0.02] border border-white/[0.05] hover:border-white/12 transition-all space-y-2"
                  >
                    <div className="flex items-start justify-between gap-2">
                      <div className="min-w-0 flex-1">
                        <div className="flex items-center gap-2 flex-wrap">
                          <h4 className="text-xs font-semibold text-slate-200 font-mono truncate">
                            {server.display_name}
                          </h4>
                          <span className="text-[9px] font-mono px-1.5 py-0.5 rounded bg-white/[0.04] border border-white/[0.06] text-slate-400">
                            DORMANT
                          </span>
                        </div>
                        <p className="text-[11px] text-slate-400 mt-1 leading-snug font-sans">
                          {server.description}
                        </p>
                      </div>

                      {onConnectServer && (
                        <button
                          onClick={() => handleConnect(server.pack_id)}
                          disabled={isConnecting}
                          className="px-3 py-1.5 rounded-xl bg-white hover:bg-white/90 text-black text-[10px] font-mono font-semibold uppercase tracking-wider transition-all duration-200 cursor-pointer shadow-[0_2px_10px_rgba(255,255,255,0.12)] active:scale-95 disabled:opacity-40 shrink-0 flex items-center gap-1"
                          title="Manually connect this server and index its tools"
                        >
                          {isConnecting ? (
                            <>
                              <span className="w-3 h-3 border-2 border-black/30 border-t-black rounded-full animate-spin" />
                              <span>Connecting...</span>
                            </>
                          ) : (
                            <span>+ Connect</span>
                          )}
                        </button>
                      )}
                    </div>

                    {server.env_vars && server.env_vars.length > 0 && (
                      <div className="flex items-center gap-1.5 flex-wrap pt-1 text-[9px] font-mono text-slate-500">
                        <span>Requires:</span>
                        {server.env_vars.map(v => (
                          <span key={v} className="px-1.5 py-0.5 rounded bg-white/[0.03] border border-white/[0.06] text-slate-400">
                            {v}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>

        </div>

        {/* Bottom Status Footer */}
        <div className="px-5 py-3.5 border-t border-white/[0.06] bg-white/[0.02] backdrop-blur-md flex items-center justify-between text-[10px] font-mono text-slate-400">
          <span>Total Indexed Tools: {telemetry?.total_indexed_tools ?? 0}</span>
          <span className="flex items-center gap-1.5">
            <span className="w-1.5 h-1.5 rounded-full bg-white shadow-[0_0_6px_rgba(255,255,255,0.7)]" />
            Dynamic FAISS Index
          </span>
        </div>
      </aside>
    </>
  );
};

export default McpToolsDrawer;

