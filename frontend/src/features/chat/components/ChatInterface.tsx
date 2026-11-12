import React, { useState, useEffect, useRef, useCallback } from 'react';
import { BorderBeam } from 'border-beam';
import { Liquid } from 'liquid-gooey';
import { AnimatedTopDock } from '../../../shared/components/layout/AnimatedTopDock';
import { ThemeSelector } from '../../../shared/components/layout/ThemeSelector';
import {
  ConstellationFieldBackground,
  GoldVeinsBackground,
  ParticleDriftBackground
} from '../../../shared/components/backgrounds';
import { useTheme } from '../../../shared/context/ThemeContext';
import '../../../shared/shaders/threeui.css';

import {
  type Message,
  type ChatSession,
  loadChatSessions,
  saveChatSessions,
  setActiveSessionId,
  generateSessionId,
  generateSessionTitle,
  fetchChatHistoryFromApi,
  saveChatSessionToApi,
  renameChatSessionInApi,
  deleteChatSessionInApi,
  clearAllChatSessionsInApi,
  syncHistoryFromLangSmith,
  getSessionToRestoreOnMount,
  setTabActiveSessionId
} from '../services/chatHistory';
import ChatHistoryDrawer from './ChatHistoryDrawer';
import McpToolsDrawer, { type McpStatusTelemetry } from './McpToolsDrawer';
import ChatLeftRail from './ChatLeftRail';
import { CognitiveTelemetryCard, type TelemetryData } from './CognitiveTelemetryCard';
import { CompletedTelemetryBadge } from './CompletedTelemetryBadge';
import { getApiBaseUrl, getWsBaseUrl, getMokaToken, setMokaToken } from '../../../shared/utils';

interface ChatInterfaceProps {
  onBackToLanding?: () => void;
}

export const ChatInterface: React.FC<ChatInterfaceProps> = ({ onBackToLanding }) => {
  const { theme } = useTheme();
  const isBlackIce = theme === 'black-ice';
  const isRoyal = theme === 'royal';
  const isIT = theme === 'it';

  const [token, setToken] = useState<string>(() => getMokaToken());

  useEffect(() => {
    const fetchLocalToken = async () => {
      try {
        const res = await fetch(`${getApiBaseUrl()}/api/token/local`);
        if (res.ok) {
          const data = await res.json();
          if (data.token) {
            setToken(data.token);
            setMokaToken(data.token);
          }
        }
      } catch (err) {
        console.warn("Failed to automatically retrieve local token:", err);
      }
    };
    fetchLocalToken();
  }, []);

  const [sessions, setSessions] = useState<ChatSession[]>(() => loadChatSessions());
  const [isHistoryOpen, setIsHistoryOpen] = useState(false);
  const [autoFocusSearch, setAutoFocusSearch] = useState(false);
  const isSessionLoadingRef = useRef(false);

  // MCP Tools Drawer State & Telemetry
  const [isMcpToolsOpen, setIsMcpToolsOpen] = useState(false);
  const [mcpTelemetry, setMcpTelemetry] = useState<McpStatusTelemetry | null>(null);
  const [isMcpLoading, setIsMcpLoading] = useState(false);

  const fetchMcpStatus = useCallback(async () => {
    try {
      setIsMcpLoading(true);
      const res = await fetch(`${getApiBaseUrl()}/api/mcp/status`, {
        headers: token ? { Authorization: `Bearer ${token}` } : {}
      });
      if (res.ok) {
        const data = await res.json();
        if (data?.telemetry) {
          setMcpTelemetry(data.telemetry);
        }
      }
    } catch (e) {
      console.warn('[MCP Telemetry] Failed to fetch status:', e);
    } finally {
      setIsMcpLoading(false);
    }
  }, [token]);

  useEffect(() => {
    fetchMcpStatus();
  }, [fetchMcpStatus]);

  useEffect(() => {
    if (isMcpToolsOpen) {
      fetchMcpStatus();
    }
  }, [isMcpToolsOpen, fetchMcpStatus]);

  const handleDisconnectMcpServer = useCallback(async (packId: string) => {
    const res = await fetch(`${getApiBaseUrl()}/api/mcp/disconnect`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {})
      },
      body: JSON.stringify({ pack_id: packId })
    });
    if (!res.ok) {
      const errData = await res.json().catch(() => ({}));
      throw new Error(errData?.detail || `Failed to disconnect ${packId}`);
    }
    await fetchMcpStatus();
  }, [token, fetchMcpStatus]);

  const handleConnectMcpServer = useCallback(async (packId: string) => {
    const res = await fetch(`${getApiBaseUrl()}/api/mcp/connect`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {})
      },
      body: JSON.stringify({ pack_id: packId })
    });
    if (!res.ok) {
      const errData = await res.json().catch(() => ({}));
      throw new Error(errData?.detail || `Failed to connect ${packId}`);
    }
    await fetchMcpStatus();
  }, [token, fetchMcpStatus]);

  const [sessionId, setSessionId] = useState<string>(() => {
    const restoreId = getSessionToRestoreOnMount();
    const initialSessions = loadChatSessions();
    if (restoreId && initialSessions.some(s => s.id === restoreId)) {
      setTabActiveSessionId(restoreId);
      return restoreId;
    }
    // First time visiting chat page: open a clean, fresh new chat session
    const newId = generateSessionId();
    setTabActiveSessionId(newId);
    return newId;
  });

  const [messages, setMessages] = useState<Message[]>(() => {
    const restoreId = getSessionToRestoreOnMount();
    const initialSessions = loadChatSessions();
    if (restoreId) {
      const activeSession = initialSessions.find(s => s.id === restoreId);
      if (activeSession && activeSession.messages.length > 0) {
        return activeSession.messages;
      }
    }
    return [];
  });

  const [isConversationStarted, setIsConversationStarted] = useState(() => {
    const restoreId = getSessionToRestoreOnMount();
    const initialSessions = loadChatSessions();
    if (restoreId) {
      const activeSession = initialSessions.find(s => s.id === restoreId);
      return !!(activeSession && activeSession.messages.length > 0);
    }
    return false;
  });

  const [inputText, setInputText] = useState('');
  const [isInputFocused, setIsInputFocused] = useState(true);
  const [open, setOpen] = useState(false);
  const [isMokaTyping, setIsMokaTyping] = useState(false);
  const [isMokaThinking, setIsMokaThinking] = useState(false);
  const [pendingQueue, setPendingQueue] = useState<{ id: string; text: string; timestamp: string }[]>([]);

  // Human-In-The-Loop MCP Tool Addition State
  const [pendingInterrupt, setPendingInterrupt] = useState<{
    interrupt_type?: string;
    server_pack_id?: string;
    tool_name?: string;
    display_name?: string;
    description?: string;
    message?: string;
    proposed_args?: Record<string, any>;
  } | null>(null);
  const [isResuming, setIsResuming] = useState(false);

  // Real-time Cognitive Telemetry State
  const [cognitiveTelemetry, setCognitiveTelemetry] = useState<TelemetryData>({
    stage: 'intent',
    title: 'INTENT ROUTER',
    text: 'Analyzing user query & checking semantic reflexes...',
    step: 1,
    provider: 'local',
    elapsedSeconds: 0,
  });
  const telemetryTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const telemetryStartTimeRef = useRef<number>(0);

  const [isMuted, setIsMuted] = useState(() => {
    return localStorage.getItem('moka_chat_muted') === 'true';
  });

  const [modelMode, setModelMode] = useState<'local' | 'cloud'>(() => {
    return (localStorage.getItem('moka_model_mode') as 'local' | 'cloud') || 'local';
  });

  // Cozmo Connection & Physical Voice Listener State
  const [isCozmoConnected, setIsCozmoConnected] = useState(false);
  const [isCozmoConnecting, setIsCozmoConnecting] = useState(false);
  const [cozmoError, setCozmoError] = useState<string | null>(null);
  const cozmoConnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const wsRef = useRef<WebSocket | null>(null);

  // Synchronize current messages to active session in sessions, localStorage & backend DB
  useEffect(() => {
    if (messages.length === 0 || isSessionLoadingRef.current) return;

    setSessions(prevSessions => {
      const existingIndex = prevSessions.findIndex(s => s.id === sessionId);
      let nextSessions: ChatSession[];

      if (existingIndex >= 0) {
        const existing = prevSessions[existingIndex];
        const updated: ChatSession = {
          ...existing,
          updatedAt: Date.now(),
          messages,
          modelMode
        };
        nextSessions = [
          updated,
          ...prevSessions.filter((_, idx) => idx !== existingIndex)
        ];
      } else {
        const firstUserMsg = messages.find(m => m.sender === 'user')?.text || 'New Conversation';
        const newSession: ChatSession = {
          id: sessionId,
          title: generateSessionTitle(firstUserMsg),
          createdAt: Date.now(),
          updatedAt: Date.now(),
          messages,
          modelMode
        };
        nextSessions = [newSession, ...prevSessions];
      }

      saveChatSessions(nextSessions);
      saveChatSessionToApi(nextSessions[0], token);
      return nextSessions;
    });
  }, [messages, sessionId, modelMode, token]);

  // Load persistent history from backend database on mount
  useEffect(() => {
    fetchChatHistoryFromApi(token).then(dbSessions => {
      if (dbSessions && dbSessions.length > 0) {
        setSessions(dbSessions);
      }
    });
  }, [token]);

  const [isSyncingLangSmith, setIsSyncingLangSmith] = useState(false);
  const [syncNotice, setSyncNotice] = useState<string | null>(null);

  const handleSyncLangSmith = useCallback(async () => {
    setIsSyncingLangSmith(true);
    setSyncNotice(null);
    try {
      const result = await syncHistoryFromLangSmith(token);
      if (result.sessions.length > 0) {
        setSessions(result.sessions);
        setSyncNotice(`Synced ${result.syncedCount} conversations from LangSmith!`);
        setTimeout(() => setSyncNotice(null), 4000);
      } else {
        setSyncNotice('No new conversations found in LangSmith.');
        setTimeout(() => setSyncNotice(null), 3000);
      }
    } catch {
      setSyncNotice('Failed to sync from LangSmith.');
      setTimeout(() => setSyncNotice(null), 3000);
    } finally {
      setIsSyncingLangSmith(false);
    }
  }, [token]);

  const handleSelectSession = useCallback((selectedSession: ChatSession) => {
    isSessionLoadingRef.current = true;
    setSessionId(selectedSession.id);
    setActiveSessionId(selectedSession.id);
    setTabActiveSessionId(selectedSession.id);
    setMessages(selectedSession.messages);
    setIsConversationStarted(selectedSession.messages.length > 0);
    setPendingQueue([]);
    setIsHistoryOpen(false);
    setTimeout(() => {
      isSessionLoadingRef.current = false;
    }, 100);
  }, []);

  const handleNewChat = useCallback(() => {
    const newId = generateSessionId();
    setSessionId(newId);
    setActiveSessionId(newId);
    setTabActiveSessionId(newId);
    setMessages([]);
    setIsConversationStarted(false);
    setPendingQueue([]);
    setIsMokaThinking(false);
    setIsMokaTyping(false);
    setInputText('');
    setIsHistoryOpen(false);
    inputRef.current?.focus();
  }, []);

  const handleDeleteSession = useCallback((idToDelete: string) => {
    deleteChatSessionInApi(idToDelete, token);
    setSessions(prev => {
      const nextSessions = prev.filter(s => s.id !== idToDelete);
      saveChatSessions(nextSessions);
      return nextSessions;
    });

    if (idToDelete === sessionId) {
      const newId = generateSessionId();
      setSessionId(newId);
      setActiveSessionId(newId);
      setTabActiveSessionId(newId);
      setMessages([]);
      setIsConversationStarted(false);
      setPendingQueue([]);
    }
  }, [sessionId, token]);

  const handleRenameSession = useCallback((idToRename: string, newTitle: string) => {
    renameChatSessionInApi(idToRename, newTitle, token);
    setSessions(prev => {
      const nextSessions = prev.map(s => s.id === idToRename ? { ...s, title: newTitle } : s);
      saveChatSessions(nextSessions);
      return nextSessions;
    });
  }, [token]);

  const handleClearAll = useCallback(() => {
    clearAllChatSessionsInApi(token);
    setSessions([]);
    saveChatSessions([]);
    const newId = generateSessionId();
    setSessionId(newId);
    setActiveSessionId(newId);
    setTabActiveSessionId(newId);
    setMessages([]);
    setIsConversationStarted(false);
    setPendingQueue([]);
    setIsHistoryOpen(false);
  }, [token]);

  // Global Keyboard Shortcuts: Ctrl+J for New Chat, Ctrl+H for Chat History
  useEffect(() => {
    const handleGlobalShortcuts = (e: KeyboardEvent) => {
      // Don't intercept shortcuts when typing inside form inputs / textareas
      const activeEl = document.activeElement;
      const isInput = activeEl && (activeEl.tagName === 'INPUT' || activeEl.tagName === 'TEXTAREA' || activeEl.getAttribute('contenteditable') === 'true');
      if (isInput) return;

      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'j') {
        e.preventDefault();
        handleNewChat();
      } else if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'h') {
        e.preventDefault();
        setAutoFocusSearch(false);
        setIsHistoryOpen(prev => !prev);
      }
    };
    window.addEventListener('keydown', handleGlobalShortcuts);
    return () => window.removeEventListener('keydown', handleGlobalShortcuts);
  }, [handleNewChat]);

  useEffect(() => {
    localStorage.setItem('moka_chat_muted', String(isMuted));
  }, [isMuted]);

  useEffect(() => {
    localStorage.setItem('moka_model_mode', modelMode);
  }, [modelMode]);

  const handleToggleModelMode = async (newMode: 'local' | 'cloud') => {
    setModelMode(newMode);
    try {
      const headers: Record<string, string> = {
        'Content-Type': 'application/json',
      };
      if (token) {
        headers['X-Moka-Token'] = token;
      }
      await fetch(`${getApiBaseUrl()}/api/model-mode`, {
        method: 'POST',
        headers,
        body: JSON.stringify({ provider: newMode })
      });
    } catch (err) {
      console.warn("Failed to sync model mode to backend:", err);
    }
  };

  const handleToggleMute = async () => {
    const nextMuted = !isMuted;
    setIsMuted(nextMuted);

    if (nextMuted) {
      try {
        const headers: Record<string, string> = {
          'Content-Type': 'application/json',
        };
        if (token) {
          headers['X-Moka-Token'] = token;
        }

        await fetch(`${getApiBaseUrl()}/api/mute`, {
          method: 'POST',
          headers,
        });
      } catch (err) {
        console.warn("Failed to notify backend of mute interrupt:", err);
      }
    }
  };

  // Cozmo Initial Status Probe on mount
  useEffect(() => {
    let isMounted = true;
    const probeCozmoStatus = async () => {
      try {
        const res = await fetch(`${getApiBaseUrl()}/api/cozmo/status`);
        if (res.ok && isMounted) {
          const data = await res.json();
          const connected = Boolean(data.is_connected);
          const connecting = Boolean(data.is_connecting);
          setIsCozmoConnected(connected);
          setIsCozmoConnecting(connecting);
          if (connected) {
            setCozmoError(null);
          } else if (data.last_error) {
            setCozmoError(data.last_error);
          }
        }
      } catch {
        // Cozmo backend starting up or idle
      }
    };
    probeCozmoStatus();
    return () => {
      isMounted = false;
    };
  }, []);

  // Active status polling fallback while Cozmo is connecting
  useEffect(() => {
    if (!isCozmoConnecting) return;
    let isCancelled = false;

    const pollInterval = setInterval(async () => {
      try {
        const res = await fetch(`${getApiBaseUrl()}/api/cozmo/status`);
        if (res.ok && !isCancelled) {
          const data = await res.json();
          if (!data.is_connecting) {
            setIsCozmoConnecting(false);
            const connected = Boolean(data.is_connected);
            setIsCozmoConnected(connected);
            if (connected) {
              setCozmoError(null);
              setIsMuted(false);
            } else {
              const errMsg = data.last_error || 'Connection failed: Cozmo robot not found. Verify robot is ON and connected to Cozmo_XXXXXX Wi-Fi.';
              setCozmoError(errMsg);
            }
          }
        }
      } catch {
        // Network fluctuation during Wi-Fi switch
      }
    }, 1500);

    return () => {
      isCancelled = true;
      clearInterval(pollInterval);
    };
  }, [isCozmoConnecting]);

  // Cozmo Voice & Telemetry WebSocket Lifecycle
  useEffect(() => {
    let isCancelled = false;
    let reconnectTimeout: ReturnType<typeof setTimeout>;

    const connectVoiceWs = () => {
      if (isCancelled) return;
      const wsUrl = `${getWsBaseUrl()}/ws/cozmo/voice?session_id=${encodeURIComponent(sessionId)}`;
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.type === 'cozmo_voice_status') {
            const connected = Boolean(data.is_connected);
            const connecting = Boolean(data.is_connecting);
            setIsCozmoConnected(connected);
            setIsCozmoConnecting(connecting);

            if (connected) {
              // Unmute when Cozmo is connected so audio outputs from Cozmo's speaker
              setIsMuted(false);
              setCozmoError(null);
              if (cozmoConnectTimeoutRef.current) {
                clearTimeout(cozmoConnectTimeoutRef.current);
                cozmoConnectTimeoutRef.current = null;
              }
            } else if (!connecting) {
              if (cozmoConnectTimeoutRef.current) {
                clearTimeout(cozmoConnectTimeoutRef.current);
                cozmoConnectTimeoutRef.current = null;
              }
              if (data.state === 'WIFI_TIMEOUT' || data.state === 'FAILED' || data.error) {
                setCozmoError(
                  data.error || 'Connection failed: Cozmo robot not found. Verify robot is ON and connected to Cozmo_XXXXXX Wi-Fi.'
                );
              }
            }
          } else if (data.type === 'user_voice_message') {
            const voiceText = data.text;
            if (voiceText) {
              const userMsg: Message = {
                id: `v_user_${Date.now()}`,
                text: voiceText,
                sender: 'user',
                timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
                telemetry: { provider: modelMode }
              };
              setMessages(prev => [...prev, userMsg]);
              setIsConversationStarted(true);
              setIsMokaThinking(true);
              setIsMokaTyping(false);
            }
          } else if (data.type === 'agent_voice_response') {
            const replyText = data.text;
            if (replyText) {
              const aiMsg: Message = {
                id: `v_ai_${Date.now()}`,
                text: replyText,
                sender: 'moka',
                timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
                telemetry: { provider: modelMode }
              };
              setMessages(prev => [...prev, aiMsg]);
              setIsMokaThinking(false);
              setIsMokaTyping(false);
            }
          } else if (data.type === 'listener_state') {
            if (data.state === 'PROCESSING') {
              setIsMokaThinking(true);
            } else if (data.state === 'SPEAKING' || data.state === 'EXPECTANT_WINDOW') {
              setIsMokaThinking(false);
            }
          }
        } catch (err) {
          console.warn('[CozmoVoiceWS] Error processing message:', err);
        }
      };

      ws.onclose = () => {
        if (!isCancelled) {
          reconnectTimeout = setTimeout(connectVoiceWs, 3000);
        }
      };

      ws.onerror = () => {
        ws.close();
      };
    };

    connectVoiceWs();

    return () => {
      isCancelled = true;
      if (reconnectTimeout) clearTimeout(reconnectTimeout);
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
    };
  }, [sessionId, modelMode]);

  // Sync session changes over WebSocket to attach voice transcripts to current conversation
  useEffect(() => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({
        action: 'set_session',
        session_id: sessionId
      }));
    }
  }, [sessionId]);

  // Toggle Cozmo Connection & Physical Voice Listener
  const handleToggleCozmo = useCallback(async () => {
    if (isCozmoConnecting) return;

    if (isCozmoConnected) {
      // Disconnect Cozmo
      setIsCozmoConnecting(false);
      setIsCozmoConnected(false);
      setCozmoError(null);
      if (cozmoConnectTimeoutRef.current) {
        clearTimeout(cozmoConnectTimeoutRef.current);
        cozmoConnectTimeoutRef.current = null;
      }
      try {
        await fetch(`${getApiBaseUrl()}/api/cozmo/disconnect`, { method: 'POST' });
      } catch (err) {
        console.warn("Failed to disconnect Cozmo:", err);
      }
    } else {
      // Connect to Cozmo
      setIsCozmoConnecting(true);
      setCozmoError(null);
      setIsMuted(false); // Switch speech output to Cozmo speaker

      // Start safety client-side timeout timer (16s fallback)
      if (cozmoConnectTimeoutRef.current) {
        clearTimeout(cozmoConnectTimeoutRef.current);
      }
      cozmoConnectTimeoutRef.current = setTimeout(() => {
        setIsCozmoConnecting(prev => {
          if (prev) {
            setCozmoError('Connection timed out. Robot did not respond. Verify Cozmo is ON and connected to Cozmo_XXXXXX Wi-Fi.');
            return false;
          }
          return prev;
        });
      }, 16000);

      try {
        const res = await fetch(`${getApiBaseUrl()}/api/cozmo/connect`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ session_id: sessionId })
        });
        if (!res.ok) {
          if (cozmoConnectTimeoutRef.current) {
            clearTimeout(cozmoConnectTimeoutRef.current);
            cozmoConnectTimeoutRef.current = null;
          }
          setIsCozmoConnecting(false);
          setCozmoError('Failed to initiate Cozmo connection.');
        }
      } catch (err) {
        console.error("Failed to connect Cozmo:", err);
        if (cozmoConnectTimeoutRef.current) {
          clearTimeout(cozmoConnectTimeoutRef.current);
          cozmoConnectTimeoutRef.current = null;
        }
        setIsCozmoConnecting(false);
        setCozmoError('Cannot reach local server. Ensure backend is running.');
      }
    }
  }, [isCozmoConnected, isCozmoConnecting, sessionId]);


  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const messagesEndRef = useRef<HTMLDivElement | null>(null);
  const inputRef = useRef<HTMLInputElement | null>(null);
  const mouseRef = useRef({ x: 0, y: 0 });
  const mouseTargetRef = useRef({ x: 0, y: 0 });
  const mousePosTargetRef = useRef({ x: -9999, y: -9999 });
  const animationFrameId = useRef<number | null>(null);

  // Document RAG Upload & Ingestion State
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const uploadPollIntervalRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const uploadAttemptIdRef = useRef(0);
  const [isDraggingFile, setIsDraggingFile] = useState(false);
  const [activeUpload, setActiveUpload] = useState<{
    file: File;
    jobId?: string;
    status: 'uploading' | 'processing' | 'completed' | 'failed';
    progress: number;
    error?: string;
    result?: any;
  } | null>(null);
  const [isDocFocusEnabled, setIsDocFocusEnabled] = useState(false);
  const isDocFocusActive = activeUpload?.status === 'completed' && isDocFocusEnabled;
  const ragOnlyRef = useRef(false);

  useEffect(() => {
    ragOnlyRef.current = isDocFocusActive;
  }, [isDocFocusActive]);

  const clearUploadPolling = useCallback(() => {
    if (uploadPollIntervalRef.current) {
      clearTimeout(uploadPollIntervalRef.current);
      uploadPollIntervalRef.current = null;
    }
  }, []);

  useEffect(() => {
    return () => {
      uploadAttemptIdRef.current += 1;
      clearUploadPolling();
    };
  }, [clearUploadPolling]);

  const handleUploadFile = useCallback(async (file: File) => {
    const validExtensions = ['.pdf', '.docx', '.doc', '.txt', '.md'];
    const ext = file.name.includes('.') ? '.' + file.name.split('.').pop()?.toLowerCase() : '';
    if (!validExtensions.includes(ext)) {
      setActiveUpload({
        file,
        status: 'failed',
        progress: 0,
        error: 'Unsupported file type. Please upload a PDF, DOCX, TXT, or Markdown document.',
      });
      return;
    }
    if (file.size === 0) {
      setActiveUpload({
        file,
        status: 'failed',
        progress: 0,
        error: 'The selected document is empty.',
      });
      return;
    }

    clearUploadPolling();
    const attemptId = ++uploadAttemptIdRef.current;

    setIsDocFocusEnabled(false);
    setActiveUpload({
      file,
      status: 'uploading',
      progress: 15,
    });

    try {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('namespace', 'documents');

      const headers: Record<string, string> = {};
      if (token) {
        headers['X-Moka-Token'] = token;
        headers['Authorization'] = `Bearer ${token}`;
      }

      const response = await fetch(`${getApiBaseUrl()}/api/documents/upload`, {
        method: 'POST',
        headers,
        body: formData,
      });

      if (!response.ok) {
        const err = await response.json().catch(() => ({}));
        throw new Error(err.detail || err.message || `Upload failed with status ${response.status}`);
      }

      const data = await response.json();
      if (attemptId !== uploadAttemptIdRef.current) return;

      if (data?.status === 'error' || data?.error) {
        throw new Error(data.message || data.detail || data.error || 'Document upload failed.');
      }

      const jobId = data.job_id;
      if (!jobId) {
        setActiveUpload({
          file,
          status: 'completed',
          progress: 100,
          result: data,
        });
        setIsDocFocusEnabled(true);
        return;
      }

      setActiveUpload({
        file,
        jobId,
        status: 'processing',
        progress: 25,
      });

      let consecutiveErrors = 0;
      let pollCount = 0;
      const MAX_POLLS = 120; // 3 minutes at 1.5s interval

      const scheduleNextPoll = () => {
        if (attemptId !== uploadAttemptIdRef.current) return;
        uploadPollIntervalRef.current = setTimeout(pollOnce, 1500);
      };

      const pollOnce = async () => {
        if (attemptId !== uploadAttemptIdRef.current) {
          clearUploadPolling();
          return;
        }
        pollCount += 1;
        if (pollCount > MAX_POLLS) {
          clearUploadPolling();
          setActiveUpload({
            file,
            jobId,
            status: 'failed',
            progress: 100,
            error: 'Document indexing timed out. Please check the Semantic ETL service.',
          });
          return;
        }

        try {
          const pollHeaders: Record<string, string> = {};
          if (token) {
            pollHeaders['X-Moka-Token'] = token;
            pollHeaders['Authorization'] = `Bearer ${token}`;
          }
          const jobRes = await fetch(`${getApiBaseUrl()}/api/documents/jobs/${jobId}`, {
            headers: pollHeaders,
          });
          if (attemptId !== uploadAttemptIdRef.current) return;

          if (!jobRes.ok) {
            consecutiveErrors += 1;
            const errBody = await jobRes.json().catch(() => ({}));
            if (attemptId !== uploadAttemptIdRef.current) return;
            if (jobRes.status >= 400 && jobRes.status < 500 || consecutiveErrors >= 3) {
              clearUploadPolling();
              setActiveUpload({
                file,
                jobId,
                status: 'failed',
                progress: 100,
                error: errBody.detail || errBody.message || `Job status check failed (HTTP ${jobRes.status})`,
              });
              return;
            }
            scheduleNextPoll();
            return;
          }

          consecutiveErrors = 0;
          const jobData = await jobRes.json();
          if (attemptId !== uploadAttemptIdRef.current) return;

          if (jobData.status === 'completed') {
            clearUploadPolling();
            setActiveUpload({
              file,
              jobId,
              status: 'completed',
              progress: 100,
              result: jobData.result,
            });
            setIsDocFocusEnabled(true);
            return;
          }
          if (jobData.status === 'failed' || jobData.status === 'error') {
            clearUploadPolling();
            setActiveUpload({
              file,
              jobId,
              status: 'failed',
              progress: 100,
              error: jobData.error || jobData.message || 'Document indexing failed',
            });
            return;
          }

          const prog = Math.max(25, Math.min(95, Math.round(jobData.progress || 35)));
          setActiveUpload(prev => (prev && prev.jobId === jobId ? { ...prev, progress: prog } : prev));
          scheduleNextPoll();
        } catch (pollErr) {
          if (attemptId !== uploadAttemptIdRef.current) return;
          consecutiveErrors += 1;
          console.error('Job polling error:', pollErr);
          if (consecutiveErrors >= 3) {
            clearUploadPolling();
            setActiveUpload({
              file,
              jobId,
              status: 'failed',
              progress: 100,
              error: 'Lost connection while tracking document indexing.',
            });
            return;
          }
          scheduleNextPoll();
        }
      };

      scheduleNextPoll();
    } catch (err: any) {
      if (attemptId !== uploadAttemptIdRef.current) return;
      console.error('Document upload error:', err);
      setActiveUpload({
        file,
        status: 'failed',
        progress: 0,
        error: err.message || 'Failed to upload document. Please ensure Semantic-ETL-Pipeline is running.',
      });
    }
  }, [token, clearUploadPolling]);

  // Auto-focus input when entering the chat page
  useEffect(() => {
    inputRef.current?.focus();
    const frameId = requestAnimationFrame(() => {
      inputRef.current?.focus();
    });
    return () => cancelAnimationFrame(frameId);
  }, []);

  // Sync isConversationStarted to a ref to prevent state-closure stale bugs in the canvas loop
  const isConversationStartedRef = useRef(false);
  useEffect(() => {
    isConversationStartedRef.current = isConversationStarted;
  }, [isConversationStarted]);

  // Track active typing to animate eyes looking down and excited for 1s per length change (+ or -)
  const isTypingRef = useRef(false);
  const typingTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const prevInputLengthRef = useRef(inputText.length);

  const triggerTypingPulse = useCallback(() => {
    isTypingRef.current = true;
    if (typingTimerRef.current) {
      clearTimeout(typingTimerRef.current);
    }
    typingTimerRef.current = setTimeout(() => {
      isTypingRef.current = false;
      typingTimerRef.current = null;
    }, 1000);
  }, []);

  const resetTypingState = useCallback(() => {
    if (typingTimerRef.current) {
      clearTimeout(typingTimerRef.current);
      typingTimerRef.current = null;
    }
    isTypingRef.current = false;
  }, []);

  useEffect(() => {
    if (inputText.length !== prevInputLengthRef.current) {
      prevInputLengthRef.current = inputText.length;
      triggerTypingPulse();
    }
  }, [inputText, triggerTypingPulse]);

  useEffect(() => {
    return () => {
      if (typingTimerRef.current) {
        clearTimeout(typingTimerRef.current);
      }
    };
  }, []);

  // Header loop state to cycle between MOKA text and mini-eyes every 15 seconds
  const [headerState, setHeaderState] = useState<'moka' | 'eyes'>('moka');
  const headerStateRef = useRef<'moka' | 'eyes'>('moka');

  useEffect(() => {
    if (!isConversationStarted) {
      setHeaderState('moka');
      headerStateRef.current = 'moka';
      return;
    }

    const interval = setInterval(() => {
      const next = headerStateRef.current === 'moka' ? 'eyes' : 'moka';
      setHeaderState(next);
      headerStateRef.current = next;
    }, 4000);

    return () => clearInterval(interval);
  }, [isConversationStarted]);

  // Core Brain Connection State (polls backend /api/health)
  const [isConnected, setIsConnected] = useState(false);
  const isConnectedRef = useRef(false);
  useEffect(() => {
    isConnectedRef.current = isConnected;
  }, [isConnected]);

  useEffect(() => {
    let timeoutId: ReturnType<typeof setTimeout>;

    const checkConnection = async () => {
      try {
        const res = await fetch(`${getApiBaseUrl()}/api/health`);
        if (res.ok) {
          setIsConnected(true);
          timeoutId = setTimeout(checkConnection, 5000);
        } else {
          setIsConnected(false);
          timeoutId = setTimeout(checkConnection, 500);
        }
      } catch {
        setIsConnected(false);
        timeoutId = setTimeout(checkConnection, 500);
      }
    };

    checkConnection();
    return () => clearTimeout(timeoutId);
  }, []);

  // Scroll to bottom helper
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isMokaTyping, isMokaThinking]);

  // High-performance Particle Canvas Eye system
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const logicalW = 1200;
    const logicalH = 600;

    // Helper for rounded rectangle
    const drawRoundedRect = (
      c: CanvasRenderingContext2D,
      x: number,
      y: number,
      w: number,
      h: number,
      r: number
    ) => {
      c.beginPath();
      c.moveTo(x + r, y);
      c.lineTo(x + w - r, y);
      c.quadraticCurveTo(x + w, y, x + w, y + r);
      c.lineTo(x + w, y + h - r);
      c.quadraticCurveTo(x + w, y + h, x + w - r, y + h);
      c.lineTo(x + r, y + h);
      c.quadraticCurveTo(x, y + h, x, y + h - r);
      c.lineTo(x, y + r);
      c.quadraticCurveTo(x, y, x + r, y);
      c.closePath();
      c.fill();
    };

    // Draw eye shapes offscreen to extract pixel targets
    const tempCanvas = document.createElement('canvas');
    tempCanvas.width = logicalW;
    tempCanvas.height = logicalH;
    const tempCtx = tempCanvas.getContext('2d');
    if (!tempCtx) return;

    tempCtx.fillStyle = '#000000';
    tempCtx.fillRect(0, 0, logicalW, logicalH);
    tempCtx.fillStyle = '#ffffff';

    // Left and Right eye locations
    drawRoundedRect(tempCtx, 280, 180, 240, 240, 40);
    drawRoundedRect(tempCtx, 680, 180, 240, 240, 40);

    const eyeImgData = tempCtx.getImageData(0, 0, logicalW, logicalH);
    const eyeData = eyeImgData.data;
    const eyeTargets: { x: number; y: number }[] = [];

    const stepY = 8;
    const stepX = 5;

    for (let y = 0; y < logicalH; y += stepY) {
      for (let x = 0; x < logicalW; x += stepX) {
        const idx = (y * logicalW + x) * 4;
        if (eyeData[idx] > 128) {
          eyeTargets.push({ x, y });
        }
      }
    }

    // --- Scene: MOKA Logo Shape ---
    const tempCanvasMoka = document.createElement('canvas');
    tempCanvasMoka.width = logicalW;
    tempCanvasMoka.height = logicalH;
    const tempCtxMoka = tempCanvasMoka.getContext('2d');
    const mokaTargets: { x: number; y: number }[] = [];

    if (tempCtxMoka) {
      tempCtxMoka.fillStyle = '#000000';
      tempCtxMoka.fillRect(0, 0, logicalW, logicalH);
      tempCtxMoka.fillStyle = '#ffffff';
      tempCtxMoka.font = 'bold 100px system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif';
      tempCtxMoka.textAlign = 'left';
      tempCtxMoka.textBaseline = 'top';
      tempCtxMoka.fillText('MOKA', 0, 0);

      const mokaImgData = tempCtxMoka.getImageData(0, 0, logicalW, logicalH);
      const mokaData = mokaImgData.data;

      // Sample logo targets with stepY=8 and stepX=5 to match homepage density exactly
      for (let y = 0; y < logicalH; y += stepY) {
        for (let x = 0; x < logicalW; x += stepX) {
          const idx = (y * logicalW + x) * 4;
          if (mokaData[idx] > 128) {
            mokaTargets.push({ x, y });
          }
        }
      }
    }

    const shuffledMoka = [...mokaTargets].sort(() => Math.random() - 0.5);

    interface EyeParticle {
      x: number;
      y: number;
      eyeX: number;
      eyeY: number;
      mokaX: number;
      mokaY: number;
      size: number;
      alpha: number;
      mokaAlpha: number;
      seed: number;
      speedOffset: number;
    }

    const particles: EyeParticle[] = eyeTargets.map((target, i) => {
      const isMokaActive = i < shuffledMoka.length;
      const mokaT = isMokaActive ? shuffledMoka[i] : { x: 0, y: 0 };
      return {
        x: target.x + (Math.random() - 0.5) * 50,
        y: target.y + (Math.random() - 0.5) * 50,
        eyeX: target.x,
        eyeY: target.y,
        mokaX: mokaT.x,
        mokaY: mokaT.y,
        size: Math.random() * 1.0 + 1.8,
        alpha: 0,
        mokaAlpha: isMokaActive ? 1.0 : 0.0,
        seed: Math.random() * 100,
        speedOffset: Math.random(),
      };
    });

    let time = 0;
    let blinkTimer = 0;
    let blinkFactor = 1.0;
    let typingExcitedFactor = 0; // 0 (idle) to 1 (activated strictly when user is typing)
    let lastTimestamp = performance.now();

    const render = (now: number = performance.now()) => {
      const rawDelta = (now - lastTimestamp) / 1000;
      lastTimestamp = now;
      const delta = Math.min(Math.max(rawDelta, 0.001), 0.05);
      const dt = delta * 60;
      time += dt;

      const canvas = canvasRef.current;
      if (!canvas) return;

      const ctx = canvas.getContext('2d');
      if (!ctx) return;

      // Use window coordinates for full-viewport canvas
      const width = window.innerWidth;
      const height = window.innerHeight;

      if (canvas.width !== width || canvas.height !== height) {
        canvas.width = width;
        canvas.height = height;
      }

      ctx.clearRect(0, 0, width, height);

      // Dynamically resolve particle color from index.css
      const cssColor = getComputedStyle(document.documentElement).getPropertyValue('--particle-rgb').trim();
      const rgb = cssColor || '0, 243, 255';

      // Smoothly interpolate typing excitement factor (0 to 1) - activated strictly when typing
      const targetTyping = isTypingRef.current ? 1.0 : 0.0;
      typingExcitedFactor += (targetTyping - typingExcitedFactor) * Math.min(0.12 * dt, 1);

      // Handle blinks (more frequent & alert when excited)
      if (blinkTimer > 0) {
        blinkTimer -= dt;
        if (blinkTimer > 10) {
          blinkFactor = Math.max(0, (blinkTimer - 10) / 10); // closing
        } else {
          blinkFactor = Math.min(1, (10 - blinkTimer) / 10); // opening
        }
      } else {
        blinkFactor = 1.0;
        const blinkProbability = (0.006 + 0.006 * typingExcitedFactor) * dt;
        if (Math.random() < blinkProbability) {
          blinkTimer = 18;
        }
      }

      // Smoothly interpolate cursor position (lerp) exactly like home page ParticleCanvas
      mouseRef.current.x += (mouseTargetRef.current.x - mouseRef.current.x) * Math.min(1 * dt, 1);
      mouseRef.current.y += (mouseTargetRef.current.y - mouseRef.current.y) * Math.min(1 * dt, 1);

      // Scale matrix to fit screen width and height uniformly with margins matching original home page
      const scale = Math.min(width / logicalW, height / logicalH) * 0.82;
      const offsetX = (width - logicalW * scale) / 2;
      const offsetY = (height - logicalH * scale) / 2;

      const isConversationStartedVal = isConversationStartedRef.current;

      for (let i = 0; i < particles.length; i++) {
        const p = particles[i];
        let targetX = 0;
        let targetY = 0;
        let pTargetAlpha = 1.0;

        if (!isConversationStartedVal) {
          // Centered Big Eyes
          const isLeftEye = p.eyeX < 600;
          const eyeCenterX = isLeftEye ? 400 : 800;
          const eyeCenterY = 300;

          const dx = p.eyeX - eyeCenterX;
          const dy = p.eyeY - eyeCenterY;

          // Mouse tracking: when typing, gaze locks downwards toward the input field
          const mouseInfluence = 1.0 - 0.75 * typingExcitedFactor;
          const mouseTilt = mouseRef.current.x * 0.10 * mouseInfluence;
          const eyeScaleBase = isLeftEye ? (1.0 - mouseTilt) : (1.0 + mouseTilt);

          // Excited uniform dilation (+8%) with a subtle organic breath
          const excitedDilation = 1.0 + (0.08 + Math.sin(time * 0.12) * 0.02) * typingExcitedFactor;
          const totalScale = eyeScaleBase * excitedDilation * (1.0 + Math.sin(time * 0.04 + p.seed) * 0.015);

          // Inquisitive, eager Cozmo tilt (\  /) — rigid rotation preserving the pristine dot scanline matrix
          const tiltAngle = (isLeftEye ? 0.06 : -0.06) * typingExcitedFactor;
          const cosA = Math.cos(tiltAngle);
          const sinA = Math.sin(tiltAngle);

          const rotX = (dx * cosA - dy * sinA) * totalScale;
          const rotY = (dx * sinA + dy * cosA) * totalScale * blinkFactor;

          // Inward focal convergence: eyes glance inward toward the input field centered below
          const focalConvergence = (isLeftEye ? 12 : -12) * typingExcitedFactor;

          // Smooth gaze shift: Downward gaze toward the message input box (+34px)
          const shiftX = mouseRef.current.x * 16 * mouseInfluence;
          const lookDownY = 34 * typingExcitedFactor;
          const shiftY = mouseRef.current.y * 12 * mouseInfluence + lookDownY;

          // Eager, happy breathing bob of the entire eye unit
          const excitedBobY = Math.sin(time * 0.15) * 3.5 * typingExcitedFactor;

          // Idle breathing
          const idleX = Math.sin(time * 0.08 + p.seed * 5) * 0.8;
          const idleY = Math.cos(time * 0.08 + p.seed * 5) * 0.6;

          targetX = (eyeCenterX + focalConvergence + rotX + shiftX) * scale + offsetX + idleX;
          targetY = (eyeCenterY + rotY + shiftY) * scale + offsetY + idleY + excitedBobY;
          pTargetAlpha = 1.0;
        } else {
          // In-conversation state: Mini eyes / Moka text in header
          const currentHeaderMode = headerStateRef.current;

          if (currentHeaderMode === 'moka') {
            // MOKA logo text shape aligned to the header
            const logoScale = 0.38;
            targetX = 48 + p.mokaX * logoScale;
            targetY = 29 + p.mokaY * logoScale;
            pTargetAlpha = p.mokaAlpha;
          } else {
            // Miniature eyes shape in the header
            const miniScale = 0.16;
            const headerCenterX = 88;
            const headerCenterY = 38;

            const cx = p.eyeX < 600 ? 400 : 800;
            const cy = 300;

            const dx_eye = p.eyeX - cx;
            const dy_eye = p.eyeY - cy;

            const isLeftEye = p.eyeX < 600;
            const eyeScale = isLeftEye
              ? (1.0 - mouseRef.current.x * 0.15)
              : (1.0 + mouseRef.current.x * 0.15);

            const scaledX = cx + dx_eye * eyeScale;
            const scaledY = cy + dy_eye * eyeScale * blinkFactor;

            const maxShiftMini = 10;
            const shiftX = mouseRef.current.x * maxShiftMini;
            const shiftYMini = mouseRef.current.y * maxShiftMini + 7 * typingExcitedFactor;
            const excitedMiniBobY = Math.sin(time * 0.18) * 1.5 * typingExcitedFactor;

            const idleX = Math.sin(time * 0.07 + p.seed * 5) * 0.3;
            const idleY = Math.cos(time * 0.07 + p.seed * 5) * 0.2;

            const relativeX = (scaledX - 600) * miniScale;
            const relativeY = (scaledY - 300) * miniScale;

            targetX = headerCenterX + relativeX + shiftX + idleX;
            targetY = headerCenterY + relativeY + shiftYMini + idleY + excitedMiniBobY;
            pTargetAlpha = 1.0;
          }
        }

        // Mouse avoidance repelling force
        const dxMouse = targetX - mousePosTargetRef.current.x;
        const dyMouse = targetY - mousePosTargetRef.current.y;
        const distMouse = Math.sqrt(dxMouse * dxMouse + dyMouse * dyMouse);

        let avoidX = 0;
        let avoidY = 0;
        const avoidanceRadius = 60;
        if (distMouse < avoidanceRadius && distMouse > 0) {
          const force = (avoidanceRadius - distMouse) / avoidanceRadius;
          const strength = force * 50;
          avoidX = (dxMouse / distMouse) * strength;
          avoidY = (dyMouse / distMouse) * strength;
        }

        targetX += avoidX;
        targetY += avoidY;

        // Dynamic easing factor: snappy tracking close by, smooth transition when far
        const dxDist = targetX - p.x;
        const dyDist = targetY - p.y;
        const dist = Math.hypot(dxDist, dyDist);
        const ease = dist > 180 ? (0.13 + p.speedOffset * 0.04) : (0.12 + p.speedOffset * 0.08);
        const effectiveEase = Math.min(1 - Math.pow(Math.max(0, 1 - ease), dt), 1);
        p.x += (targetX - p.x) * effectiveEase;
        p.y += (targetY - p.y) * effectiveEase;

        // Smoothly fade to target alpha
        p.alpha += (pTargetAlpha - p.alpha) * Math.min(0.12 * dt, 1);

        if (p.alpha > 0.01) {
          const isScaledDown = isConversationStartedVal;
          const currentSize = isScaledDown ? p.size * 0.72 * scale : p.size * scale;

          // Draw soft glowing outer aura with focus excitement boost
          const auraAlpha = p.alpha * (0.12 + 0.06 * typingExcitedFactor);
          ctx.fillStyle = `rgba(${rgb}, ${auraAlpha})`;
          ctx.beginPath();
          ctx.arc(p.x, p.y, currentSize * 1.5, 0, Math.PI * 2);
          ctx.fill();

          // Draw bright core dot
          ctx.fillStyle = `rgba(${rgb}, ${p.alpha})`;
          ctx.beginPath();
          ctx.arc(p.x, p.y, currentSize, 0, Math.PI * 2);
          ctx.fill();
        }
      }

      animationFrameId.current = requestAnimationFrame(render);
    };

    render();

    // Mouse movement listener
    const handleMouseMove = (e: MouseEvent) => {
      const cx = window.innerWidth / 2;
      const cy = window.innerHeight / 2;
      mouseTargetRef.current = {
        x: (e.clientX - cx) / cx,
        y: (e.clientY - cy) / cy,
      };
      mousePosTargetRef.current = {
        x: e.clientX,
        y: e.clientY,
      };
    };

    window.addEventListener('mousemove', handleMouseMove);

    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
      if (animationFrameId.current) {
        cancelAnimationFrame(animationFrameId.current);
      }
    };
  }, []);

  // Context-aware replies mock response logic returning a Promise
  const triggerMockMokaResponse = useCallback((userMsg: string): Promise<void> => {
    setIsMokaThinking(true);
    setIsMokaTyping(true);

    return new Promise((resolve) => {
      setTimeout(() => {
        let reply = "I am checking my local systems for that task. What would you like to build?";
        const cleaned = userMsg.toLowerCase();

        if (cleaned.includes('memory') || cleaned.includes('short-term') || cleaned.includes('long-term')) {
          reply = "MoKa uses a dual-layer memory system: PostgresSaver indexes recent message threads, while our local FastEmbed implementation manages long-term RAG lookups across files.";
        } else if (cleaned.includes('cozmo') || cleaned.includes('robot') || cleaned.includes('control')) {
          reply = "My low-latency physical bridge is active. I can steering-dock to the charger using cv2 HSV filters, query paths, or animate OLED face expressions.";
        } else if (cleaned.includes('llm') || cleaned.includes('ollama') || cleaned.includes('model')) {
          reply = "MoKa is connected to your local Ollama engine. I am currently running Qwen 2.5 (7B) for deep cognition and Gemma 2 for lower latency routing checkpoints.";
        } else if (cleaned.includes('hello') || cleaned.includes('hi') || cleaned.includes('hey')) {
          reply = "Hello! I am MoKa, your local autonomous AI companion. I'm connected to the local Ollama brain. How can I assist you with your workspace or Cozmo today?";
        } else if (cleaned.includes('capabilities') || cleaned.includes('feature') || cleaned.includes('can you do')) {
          reply = "I manage voice triggers ('hey buddy'), index FAISS vectors, trigger workstations, coordinate Google Calendar via n8n, and run OpenAPI auto-docking cycles.";
        }

        const timestamp = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        setMessages(prev => [
          ...prev,
          {
            id: Math.random().toString(),
            sender: 'moka',
            text: reply,
            timestamp,
            telemetry: {
              elapsedSeconds: 1.2,
              tool: 'Local Companion Engine',
              provider: modelMode,
              steps: ['Episodic Memory', 'Intent Router', 'Local Companion Engine', 'Dialogue Synthesis']
            }
          }
        ]);
        setIsMokaThinking(false);
        setIsMokaTyping(false);
        resolve();
      }, 1200);
    });
  }, [modelMode]);

  // Process message stream with backend
  const processMessage = useCallback(async (messageId: string, text: string, timestamp: string) => {
    setIsMokaThinking(true);
    setIsMokaTyping(true);

    // 1. Initialize telemetry state & live timer
    telemetryStartTimeRef.current = Date.now();
    setCognitiveTelemetry({
      stage: 'intent',
      title: 'INTENT ROUTER',
      text: 'Analyzing user query & checking semantic reflexes...',
      step: 1,
      provider: modelMode,
      elapsedSeconds: 0,
    });

    if (telemetryTimerRef.current) {
      clearInterval(telemetryTimerRef.current);
    }
    telemetryTimerRef.current = setInterval(() => {
      const elapsed = (Date.now() - telemetryStartTimeRef.current) / 1000;
      setCognitiveTelemetry(prev => ({
        ...prev,
        elapsedSeconds: elapsed,
      }));
    }, 100);

    const mokaMsgId = (Date.now() + 1).toString();
    const mokaTimestamp = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    let finalTool: string | undefined = undefined;
    let accumulatedText = '';

    // Soft fallback timer progression in case of model latency
    const fallbackTimeout1 = setTimeout(() => {
      setCognitiveTelemetry(prev => {
        if (prev.step === 1 && prev.stage === 'intent') {
          return {
            ...prev,
            stage: 'memory',
            title: 'EPISODIC MEMORY',
            text: 'Scanning memory core for user context & preferences...',
            step: 1,
          };
        }
        return prev;
      });
    }, 800);

    const fallbackTimeout2 = setTimeout(() => {
      setCognitiveTelemetry(prev => {
        if (prev.step <= 2 && prev.stage !== 'executing') {
          if (ragOnlyRef.current) {
            return {
              ...prev,
              stage: 'rag',
              title: 'GROUNDED RAG',
              text: 'Searching uploaded document knowledge base...',
              step: 3,
            };
          }
          return {
            ...prev,
            stage: 'tools_rag',
            title: 'INTENT ROUTER',
            text: 'Evaluating candidate tools and conversation routes...',
            step: 2,
          };
        }
        return prev;
      });
    }, 1600);

    try {
      const headers: Record<string, string> = {
        'Content-Type': 'application/json',
      };
      if (token) {
        headers['X-Moka-Token'] = token;
      }

      const response = await fetch(`${getApiBaseUrl()}/api/chat/stream`, {
        method: 'POST',
        headers,
        body: JSON.stringify({
          message: text,
          session_id: sessionId,
          mute: isCozmoConnected ? false : isMuted,
          muted: isCozmoConnected ? false : isMuted,
          provider: modelMode,
          rag_only: ragOnlyRef.current,
          document_namespace: 'documents',
        })
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const contentType = response.headers.get('content-type') || '';
      let isInterrupted = false;

      if (contentType.includes('text/event-stream') && response.body) {
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split('\n');
          buffer = lines.pop() || '';

          for (const line of lines) {
            const trimmed = line.trim();
            if (!trimmed.startsWith('data: ')) continue;
            const payloadStr = trimmed.slice(6).trim();
            if (payloadStr === '[DONE]') continue;

            try {
              const data = JSON.parse(payloadStr);

              if (data.type === 'hitl_interrupt') {
                isInterrupted = true;
                setIsMokaThinking(false);
                setIsMokaTyping(false);
                setPendingInterrupt(data.payload);
                break;
              } else if (data.type === 'status') {
                if (data.tool) finalTool = data.tool;
                setCognitiveTelemetry(prev => ({
                  ...prev,
                  stage: data.stage || prev.stage,
                  title: data.title || prev.title,
                  text: data.text || prev.text,
                  step: data.step !== undefined ? data.step : prev.step,
                  tool: data.tool || prev.tool,
                  provider: data.provider || prev.provider,
                }));
              } else if (data.type === 'token' || data.token !== undefined) {
                const tokenStr = data.token !== undefined ? data.token : '';
                accumulatedText += tokenStr;

                // Stop showing the thinking orb card as soon as response tokens start streaming
                setIsMokaThinking(false);

                setMessages(prev => {
                  const exists = prev.some(m => m.id === mokaMsgId);
                  if (!exists) {
                    return [
                      ...prev,
                      {
                        id: mokaMsgId,
                        sender: 'moka',
                        text: accumulatedText,
                        timestamp: mokaTimestamp
                      }
                    ];
                  }
                  return prev.map(m => m.id === mokaMsgId ? { ...m, text: accumulatedText } : m);
                });
              }
            } catch {
              // Ignore partial JSON chunks
            }
          }

          if (isInterrupted) {
            break;
          }
        }
      } else {
        // Fallback for non-streaming response
        const data = await response.json();
        if (data.status === 'interrupt') {
          setIsMokaThinking(false);
          setIsMokaTyping(false);
          setPendingInterrupt(data.interrupt);
          return;
        }
        accumulatedText = data.response !== undefined ? data.response : (data.message !== undefined ? data.message : JSON.stringify(data));
        setIsMokaThinking(false);
      }

      clearTimeout(fallbackTimeout1);
      clearTimeout(fallbackTimeout2);
      if (telemetryTimerRef.current) {
        clearInterval(telemetryTimerRef.current);
        telemetryTimerRef.current = null;
      }

      // If an HITL interrupt occurred, do not finalize an empty message bubble
      if (isInterrupted) {
        setMessages(prev => prev.filter(m => m.id !== mokaMsgId || (m.text && m.text.trim().length > 0)));
        setIsMokaThinking(false);
        setIsMokaTyping(false);
        return;
      }

      // If no text was accumulated, do not create or leave an empty message
      if (!accumulatedText.trim()) {
        setMessages(prev => prev.filter(m => m.id !== mokaMsgId));
        setIsMokaThinking(false);
        setIsMokaTyping(false);
        return;
      }

      const totalElapsed = (Date.now() - telemetryStartTimeRef.current) / 1000;

      // Finalize message with complete telemetry metadata
      setMessages(prev => {
        const exists = prev.some(m => m.id === mokaMsgId);
        if (!exists) {
          return [
            ...prev,
            {
              id: mokaMsgId,
              sender: 'moka',
              text: accumulatedText,
              timestamp: mokaTimestamp,
              telemetry: {
                elapsedSeconds: totalElapsed,
                tool: finalTool,
                provider: modelMode,
                steps: ['Episodic Memory', 'Intent Router', finalTool || 'Neural Chat', 'Response']
              }
            }
          ];
        }
        return prev.map(msg =>
          msg.id === mokaMsgId
            ? {
                ...msg,
                text: accumulatedText,
                telemetry: {
                  elapsedSeconds: totalElapsed,
                  tool: finalTool,
                  provider: modelMode,
                  steps: ['Episodic Memory', 'Intent Router', finalTool || 'Neural Chat', 'Response']
                }
              }
            : msg
        );
      });

      setIsMokaThinking(false);
      setIsMokaTyping(false);
    } catch (error) {
      clearTimeout(fallbackTimeout1);
      clearTimeout(fallbackTimeout2);
      if (telemetryTimerRef.current) {
        clearInterval(telemetryTimerRef.current);
        telemetryTimerRef.current = null;
      }
      console.warn("Backend API stream error:", error);
      setIsMokaThinking(false);
      if (!isConnectedRef.current) {
        setMessages(prev => prev.filter(m => m.id !== messageId));
        setPendingQueue(prev => [
          { id: messageId, text, timestamp },
          ...prev
        ]);
        setIsMokaTyping(false);
      } else {
        await triggerMockMokaResponse(text);
      }
    }
  }, [token, sessionId, isMuted, isCozmoConnected, modelMode, triggerMockMokaResponse]);

  const handleResolveInterrupt = async (approved: boolean) => {
    if (!pendingInterrupt) return;
    setIsResuming(true);
    const currentInterrupt = pendingInterrupt;
    setPendingInterrupt(null);

    const mokaMsgId = Math.random().toString();
    const mokaTimestamp = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    let accumulatedText = '';
    let finalTool = currentInterrupt.server_pack_id || '';

    if (approved) {
      setIsMokaThinking(true);
      setCognitiveTelemetry(prev => ({
        ...prev,
        stage: 'hitl_gate',
        title: 'ACTIVATING MCP TOOL',
        text: `Connecting ${currentInterrupt.display_name || 'tool'} and ingesting actions...`,
        step: 2,
      }));
    }

    try {
      const headers: Record<string, string> = {
        'Content-Type': 'application/json',
      };
      if (token) {
        headers['X-Moka-Token'] = token;
      }

      const response = await fetch(`${getApiBaseUrl()}/api/chat/resume/stream`, {
        method: 'POST',
        headers,
        body: JSON.stringify({
          session_id: sessionId,
          approved,
          provider: modelMode,
          mute: isCozmoConnected ? false : isMuted
        })
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      let isInterrupted = false;

      if (response.body) {
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split('\n');
          buffer = lines.pop() || '';

          for (const line of lines) {
            const trimmed = line.trim();
            if (!trimmed.startsWith('data: ')) continue;
            const payloadStr = trimmed.slice(6).trim();
            if (payloadStr === '[DONE]') continue;

            try {
              const data = JSON.parse(payloadStr);

              if (data.type === 'hitl_interrupt') {
                isInterrupted = true;
                setIsMokaThinking(false);
                setIsMokaTyping(false);
                setPendingInterrupt(data.payload);
                break;
              } else if (data.type === 'status') {
                if (data.tool) finalTool = data.tool;
                setCognitiveTelemetry(prev => ({
                  ...prev,
                  stage: data.stage || prev.stage,
                  title: data.title || prev.title,
                  text: data.text || prev.text,
                  step: data.step !== undefined ? data.step : prev.step,
                  tool: data.tool || prev.tool,
                }));
              } else if (data.type === 'token' || data.token !== undefined) {
                const tokenStr = data.token !== undefined ? data.token : '';
                accumulatedText += tokenStr;
                setIsMokaThinking(false);

                setMessages(prev => {
                  const exists = prev.some(m => m.id === mokaMsgId);
                  if (!exists) {
                    return [
                      ...prev,
                      {
                        id: mokaMsgId,
                        sender: 'moka',
                        text: accumulatedText,
                        timestamp: mokaTimestamp
                      }
                    ];
                  }
                  return prev.map(m => m.id === mokaMsgId ? { ...m, text: accumulatedText } : m);
                });
              }
            } catch {
              // Ignore partial JSON
            }
          }

          if (isInterrupted) {
            break;
          }
        }
      }

      if (isInterrupted) {
        setMessages(prev => prev.filter(m => m.id !== mokaMsgId || (m.text && m.text.trim().length > 0)));
        return;
      }

      // Finalize with telemetry only if actual text exists
      if (accumulatedText.trim()) {
        setMessages(prev =>
          prev.map(msg =>
            msg.id === mokaMsgId
              ? {
                  ...msg,
                  telemetry: {
                    elapsedSeconds: 1.5,
                    tool: finalTool,
                    provider: modelMode,
                    steps: ['Approval Gate', 'Tool Ingestion', finalTool || 'Execution', 'Synthesis']
                  }
                }
              : msg
          )
        );
      } else {
        setMessages(prev => prev.filter(m => m.id !== mokaMsgId));
      }
    } catch (err) {
      console.error("Failed to resume interrupted turn:", err);
    } finally {
      setIsResuming(false);
      setIsMokaThinking(false);
      setIsMokaTyping(false);
    }
  };

  // Submit handler
  const handleSendMessage = async (textToSend?: string) => {
    const text = (textToSend || inputText).trim();
    if (!text) return;

    if (!isConversationStarted) {
      setIsConversationStarted(true);
      isConversationStartedRef.current = true;
    }

    const timestamp = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    const newMessage = {
      id: Math.random().toString(),
      text,
      timestamp
    };

    if (!textToSend) {
      setInputText('');
      prevInputLengthRef.current = 0;
      resetTypingState();
    }

    if (isMokaTyping || pendingQueue.length > 0 || !isConnected) {
      setPendingQueue(prev => [...prev, newMessage]);
    } else {
      const userMessage: Message = {
        id: newMessage.id,
        sender: 'user',
        text: newMessage.text,
        timestamp: newMessage.timestamp
      };
      setMessages(prev => [...prev, userMessage]);
      processMessage(newMessage.id, newMessage.text, newMessage.timestamp);
    }
  };

  const handleDeletePendingMessage = (id: string) => {
    setPendingQueue(prev => prev.filter(m => m.id !== id));
  };

  // Queue loop
  useEffect(() => {
    if (isConnected && !isMokaTyping && pendingQueue.length > 0) {
      const nextMsg = pendingQueue[0];
      setPendingQueue(prev => prev.slice(1));

      const userMessage: Message = {
        id: nextMsg.id,
        sender: 'user',
        text: nextMsg.text,
        timestamp: nextMsg.timestamp
      };
      setMessages(prev => [...prev, userMessage]);
      processMessage(nextMsg.id, nextMsg.text, nextMsg.timestamp);
    }
  }, [isConnected, isMokaTyping, pendingQueue, processMessage]);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      resetTypingState();
      handleSendMessage();
    }
  };

  return (
    <div
      onDragEnter={(e) => {
        if (!Array.from(e.dataTransfer?.types || []).includes('Files')) return;
        e.preventDefault();
        e.stopPropagation();
        setIsDraggingFile(true);
      }}
      onDragOver={(e) => {
        if (!Array.from(e.dataTransfer?.types || []).includes('Files')) return;
        e.preventDefault();
        e.stopPropagation();
        if (!isDraggingFile) setIsDraggingFile(true);
      }}
      onDragLeave={(e) => {
        e.preventDefault();
        e.stopPropagation();
        if (!e.currentTarget.contains(e.relatedTarget as Node)) {
          setIsDraggingFile(false);
        }
      }}
      onDrop={(e) => {
        if (!Array.from(e.dataTransfer?.types || []).includes('Files')) return;
        e.preventDefault();
        e.stopPropagation();
        setIsDraggingFile(false);
        const file = e.dataTransfer.files?.[0];
        if (file) {
          handleUploadFile(file);
        }
      }}
      className={`relative w-screen h-screen ${isBlackIce ? 'bg-[#020407]' : isRoyal ? 'bg-[#030407]' : isIT ? 'bg-[#020503]' : 'bg-[#030407]'
      } overflow-hidden flex flex-col transition-colors duration-700 font-sans selection:bg-[var(--brand-primary)]/30 selection:text-white`}
    >
      {/* Drag & Drop Visual Overlay */}
      {isDraggingFile && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-md pointer-events-none transition-all duration-300">
          <div className="border-2 border-dashed border-[var(--brand-primary)] bg-[var(--brand-card-bg)]/95 rounded-3xl p-10 flex flex-col items-center justify-center shadow-2xl max-w-lg mx-6 text-center animate-pulse">
            <div className="w-16 h-16 rounded-2xl bg-[var(--brand-primary)]/20 text-[var(--brand-primary)] flex items-center justify-center mb-4">
              <svg className="w-8 h-8 text-[var(--brand-primary)]" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m2.25 0H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" />
              </svg>
            </div>
            <h3 className="text-xl font-bold text-white mb-2 font-sans">Drop Document to Index</h3>
            <p className="text-sm text-slate-300 font-sans">
              Release to upload and index into MoKa's Grounded Knowledge Base (PDF, DOCX, TXT, MD)
            </p>
          </div>
        </div>
      )}


      {/* Dynamic Theme Background Shaders (85% opacity at rest matching home page, 40% when conversation is active) */}
      <div
        className="fixed inset-0 pointer-events-none z-0 transition-opacity duration-700 ease-in-out"
        style={{ opacity: isConversationStarted ? 0.40 : 0.85 }}
      >
        {/* 🌌 ThreeUI Constellation Field Background for Black Ice */}
        {isBlackIce && (
          <ConstellationFieldBackground className="w-full h-full" baseOpacity={1.0} maxOpacity={1.0} />
        )}

        {/* 👑 Liquid Kintsugi Gold Veins Background for Royal */}
        {isRoyal && (
          <GoldVeinsBackground className="w-full h-full" baseOpacity={1.0} maxOpacity={1.0} />
        )}

        {/* 💻 ThreeUI Particle Drift ASCII Background for IT */}
        {isIT && (
          <ParticleDriftBackground className="w-full h-full" />
        )}
      </div>


      {/* Slim Gemini-inspired Left Action Rail */}
      <ChatLeftRail
        onNewChat={handleNewChat}
        onToggleHistory={() => {
          setAutoFocusSearch(false);
          setIsMcpToolsOpen(false);
          setIsHistoryOpen(prev => !prev);
        }}
        isHistoryOpen={isHistoryOpen}
        historyCount={sessions.length}
        isCozmoConnected={isCozmoConnected}
        isCozmoConnecting={isCozmoConnecting}
        cozmoError={cozmoError}
        onToggleCozmo={handleToggleCozmo}
        onToggleMcpTools={() => {
          setIsHistoryOpen(false);
          setIsMcpToolsOpen(prev => !prev);
        }}
        isMcpToolsOpen={isMcpToolsOpen}
        activeMcpCount={mcpTelemetry?.total_active_servers ?? 0}
      />

      {/* Cozmo Connection Error Floating Banner Toast */}
      {cozmoError && !isCozmoConnecting && !isCozmoConnected && (
        <div
          className="fixed top-24 left-16 sm:left-20 z-40 max-w-sm sm:max-w-md w-[calc(100vw-5rem)] sm:w-auto animate-in fade-in slide-in-from-left-4 duration-300"
          role="alert"
        >
          <div className="flex items-start gap-3 p-3.5 rounded-xl bg-[#140a0e]/95 border border-rose-500/40 backdrop-blur-xl shadow-[0_12px_36px_rgba(0,0,0,0.6),0_0_20px_rgba(244,63,94,0.18)] text-slate-200">
            <div className="w-8 h-8 rounded-lg bg-rose-500/15 border border-rose-500/30 flex items-center justify-center shrink-0 text-rose-400 mt-0.5">
              <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <circle cx="12" cy="12" r="10" />
                <line x1="12" y1="8" x2="12" y2="12" />
                <line x1="12" y1="16" x2="12.01" y2="16" />
              </svg>
            </div>
            <div className="flex-1 min-w-0 pr-1">
              <div className="text-xs font-semibold uppercase tracking-wider text-rose-400 font-mono mb-0.5">
                Cozmo Connection Failed
              </div>
              <p className="text-xs text-slate-300 leading-relaxed break-words">
                {cozmoError}
              </p>
              <div className="flex items-center gap-2 mt-2.5">
                <button
                  type="button"
                  onClick={handleToggleCozmo}
                  className="text-[11px] font-medium px-2.5 py-1 rounded-md bg-rose-500/20 hover:bg-rose-500/30 text-rose-300 border border-rose-500/40 transition-colors cursor-pointer flex items-center gap-1.5"
                >
                  <svg className="w-3 h-3" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M1 4v6h6M23 20v-6h-6" />
                    <path d="M20.49 9A9 9 0 005.64 5.64L1 10m22 4l-4.64 4.36A9 9 0 013.51 15" />
                  </svg>
                  Retry Connection
                </button>
                <button
                  type="button"
                  onClick={() => setCozmoError(null)}
                  className="text-[11px] font-medium px-2 py-1 rounded text-slate-400 hover:text-white transition-colors cursor-pointer"
                >
                  Dismiss
                </button>
              </div>
            </div>
            <button
              type="button"
              onClick={() => setCozmoError(null)}
              className="text-slate-500 hover:text-slate-300 transition-colors p-1 -mr-1 -mt-1 cursor-pointer"
              title="Close notification"
              aria-label="Close notification"
            >
              <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <line x1="18" y1="6" x2="6" y2="18" />
                <line x1="6" y1="6" x2="18" y2="18" />
              </svg>
            </button>
          </div>
        </div>
      )}

      {/* Slide-out Left-side Chat History Drawer (Flyout next to left rail) */}
      <ChatHistoryDrawer
        isOpen={isHistoryOpen}
        onClose={() => {
          setIsHistoryOpen(false);
          setAutoFocusSearch(false);
        }}
        sessions={sessions}
        activeSessionId={sessionId}
        onSelectSession={handleSelectSession}
        onNewChat={handleNewChat}
        onDeleteSession={handleDeleteSession}
        onRenameSession={handleRenameSession}
        onClearAll={handleClearAll}
        onSyncLangSmith={handleSyncLangSmith}
        isSyncingLangSmith={isSyncingLangSmith}
        syncNotice={syncNotice}
        autoFocusSearch={autoFocusSearch}
      />

      {/* Slide-out Left-side MCP Tools Drawer */}
      <McpToolsDrawer
        isOpen={isMcpToolsOpen}
        onClose={() => setIsMcpToolsOpen(false)}
        telemetry={mcpTelemetry}
        isLoading={isMcpLoading}
        onRefresh={fetchMcpStatus}
        onDisconnectServer={handleDisconnectMcpServer}
        onConnectServer={handleConnectMcpServer}
      />

      {/* Sticky Top Navigation Header */}
      <header
        data-identity-state={headerState}
        className="fixed top-0 left-0 w-full h-20 md:h-24 bg-[#03060a]/85 border-b border-white/[0.06] backdrop-blur-2xl z-30 flex items-center justify-between px-6 md:px-10 overflow-visible"
      >
        {/* Left Side: Particle Logo Area */}
        <div className="flex items-center gap-3 sm:gap-4 z-20">
          <div
            onClick={onBackToLanding}
            className="w-28 sm:w-36 h-10 cursor-pointer"
            title="Back to Home"
            role="button"
            tabIndex={0}
          />
        </div>

        {/* Center: ThreeUI AnimatedTopDock - Mathematically centered in viewport */}
        <div className="absolute left-1/2 -translate-x-1/2 flex items-center justify-center pointer-events-none z-10">
          <div className="pointer-events-auto">
            <AnimatedTopDock defaultActive="chat" />
          </div>
        </div>

        {/* Right Side: Core Brain State, Token & Theme Selector */}
        <div className="flex items-center gap-2 sm:gap-3 md:gap-4 z-10">

          <div className="hidden sm:flex items-center gap-2 text-xs md:text-sm text-slate-300 font-medium tracking-wide bg-white/[0.04] border border-white/[0.08] px-3 py-1.5 rounded-full backdrop-blur-md">
            <span className={`w-2 h-2 rounded-full animate-pulse ${isConnected
              ? 'bg-emerald-400 shadow-[0_0_8px_#34d399]'
              : 'bg-rose-500 shadow-[0_0_8px_#f43f5e]'
              }`} />
            <span className="text-[11px] font-mono uppercase tracking-wider text-slate-400">
              Core: <span className={isConnected ? "text-emerald-400 font-semibold" : "text-rose-400 font-semibold"}>{isConnected ? 'Active' : 'Offline'}</span>
            </span>
          </div>

          {token && (
            <div className="hidden lg:block text-[10px] text-cyan-300 bg-cyan-950/40 border border-cyan-800/60 px-2.5 py-1 rounded-full font-mono" title={token}>
              Token: {token.length > 8 ? `${token.substring(0, 4)}...${token.substring(token.length - 4)}` : token}
            </div>
          )}

          <ThemeSelector />
        </div>
      </header>

      {/* Full-viewport canvas for fluid particle eyes and MOKA logo text */}
      <canvas
        ref={canvasRef}
        className="fixed inset-0 w-full h-full block pointer-events-none z-35"
      />

      {/* Scrollable Conversation Stream Wrapper (Active State) */}
      {isConversationStarted && (
        <div className="w-full flex-1 overflow-y-auto z-10 transition-all duration-700 pl-14 sm:pl-16">
          <div className="px-6 pt-28 pb-32 max-w-2xl mx-auto w-full flex flex-col gap-4">
            {messages
              .filter((msg) => msg.text && msg.text.trim().length > 0)
              .map((msg) => (
                <div
                  key={msg.id}
                  className={`flex flex-col max-w-[85%] ${msg.sender === 'user' ? 'self-end items-end' : 'self-start items-start'}`}
                >
                {/* Sender tag */}
                <span className="text-[10px] text-slate-400 font-mono font-semibold uppercase tracking-wider mb-1 px-1 flex items-center gap-1.5">
                  <span className={`w-1.5 h-1.5 rounded-full ${msg.sender === 'user' ? 'bg-[var(--brand-primary)]' : 'bg-slate-400'}`} />
                  {msg.sender === 'user' ? 'You' : 'MoKa'}
                </span>

                {/* If completed telemetry exists on assistant message */}
                {msg.sender === 'moka' && msg.telemetry && (
                  <CompletedTelemetryBadge telemetry={msg.telemetry} />
                )}

                {/* Message bubble */}
                <div
                  className={`p-4 rounded-2xl text-sm md:text-base leading-relaxed ${msg.sender === 'user'
                    ? 'theme-card text-white rounded-tr-none'
                    : 'rounded-tl-none text-slate-200'
                    }`}
                  style={msg.sender === 'moka' ? {
                    background: 'linear-gradient(135deg, rgba(255, 255, 255, 0.05) 0%, rgba(15, 20, 28, 0.65) 100%)',
                    backdropFilter: 'blur(32px) saturate(160%)',
                    WebkitBackdropFilter: 'blur(32px) saturate(160%)',
                    border: '1px solid rgba(255, 255, 255, 0.09)',
                    boxShadow: '0 16px 40px rgba(0, 0, 0, 0.5), inset 0 1px 0 rgba(255, 255, 255, 0.12)'
                  } : undefined}
                >
                  {msg.text}
                </div>

                {/* Timestamp & Actions */}
                {msg.sender === 'user' ? (
                  <div className="w-full flex items-center justify-between mt-1 px-1">
                    <button
                      onClick={() => handleSendMessage(msg.text)}
                      className="p-1 rounded text-slate-500 hover:text-[var(--brand-primary)] hover:bg-white/[0.05] transition-all cursor-pointer flex items-center justify-center group"
                      title="Resend this message"
                    >
                      <svg
                        className="w-3.5 h-3.5 transition-transform duration-500 ease-out group-hover:rotate-180"
                        fill="none"
                        viewBox="0 0 24 24"
                        stroke="currentColor"
                        strokeWidth={2.5}
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0l3.181 3.183a8.25 8.25 0 0013.803-3.7M4.031 9.865a8.25 8.25 0 0113.803-3.7l3.181 3.182m0-4.991v4.99"
                        />
                      </svg>
                    </button>
                    <span className="text-[9px] font-mono text-slate-500">{msg.timestamp}</span>
                  </div>
                ) : (
                  <span className="text-[9px] font-mono text-slate-500 mt-1 px-1">{msg.timestamp}</span>
                )}
              </div>
            ))}

            {/* Render pending/on-hold queued messages */}
            {pendingQueue.map((msg) => (
              <div
                key={msg.id}
                className="flex flex-col max-w-[85%] self-end items-end transition-all duration-300"
              >
                <span className="text-[10px] text-slate-400 font-mono font-semibold uppercase tracking-wider mb-1 px-1 flex items-center gap-1.5">
                  <span className="w-1.5 h-1.5 rounded-full bg-white shadow-[0_0_6px_rgba(255,255,255,0.7)]" />
                  You
                </span>
                <div
                  className="p-4 rounded-2xl text-sm md:text-base leading-relaxed text-slate-200 rounded-tr-none flex flex-col gap-2 min-w-[240px]"
                  style={{
                    background: 'linear-gradient(135deg, rgba(255, 255, 255, 0.04) 0%, rgba(15, 20, 28, 0.65) 100%)',
                    backdropFilter: 'blur(32px) saturate(160%)',
                    WebkitBackdropFilter: 'blur(32px) saturate(160%)',
                    border: '1px dashed rgba(255, 255, 255, 0.16)',
                    boxShadow: '0 12px 32px rgba(0, 0, 0, 0.45), inset 0 1px 0 rgba(255, 255, 255, 0.08)'
                  }}
                >
                  <div className="break-words">{msg.text}</div>
                  <div className="flex items-center justify-between gap-4 mt-1 pt-2 border-t border-white/[0.08]">
                    <div className="flex items-center gap-1.5 text-[10px] text-slate-400 font-mono">
                      <span className="w-1.5 h-1.5 rounded-full bg-white/70 animate-pulse" />
                      <span>Queued (On Hold)</span>
                    </div>
                    <button
                      onClick={() => handleDeletePendingMessage(msg.id)}
                      className="px-2.5 py-1 rounded-lg border border-white/[0.08] hover:border-white/20 bg-white/[0.04] hover:bg-white/[0.08] text-slate-300 hover:text-white transition-all cursor-pointer text-[11px] font-mono flex items-center gap-1 font-medium active:scale-95"
                      title="Cancel and delete from queue"
                    >
                      <svg className="w-3.5 h-3.5 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                      </svg>
                      Cancel
                    </button>
                  </div>
                </div>
                <span className="text-[9px] font-mono text-slate-500 mt-1 px-1">{msg.timestamp}</span>
              </div>
            ))}

            {/* Human-in-the-Loop Approval Card (Black & White styling matching Chat History) */}
            {pendingInterrupt && (
              <div className="flex flex-col self-start items-start max-w-[95%] sm:max-w-[85%] w-full my-2 animate-fadeIn">
                <span className="text-[10px] font-mono font-semibold uppercase tracking-widest mb-1.5 px-1 flex items-center gap-1.5 text-slate-400">
                  <span className="w-1.5 h-1.5 rounded-full bg-white shadow-[0_0_6px_rgba(255,255,255,0.7)] animate-pulse" />
                  <span className="text-white/90">
                    {pendingInterrupt.interrupt_type === 'mutating_tool' ? 'MUTATING ACTION GATE' : 'MOKA CAPABILITY GATE'}
                  </span>
                </span>
                <div
                  className="w-full p-5 rounded-2xl rounded-tl-none border border-white/[0.08] text-slate-100 flex flex-col gap-3.5 backdrop-blur-2xl transition-all duration-300"
                  style={{
                    background: 'linear-gradient(135deg, rgba(255, 255, 255, 0.05) 0%, rgba(10, 14, 22, 0.85) 100%)',
                    backdropFilter: 'blur(32px) saturate(160%)',
                    WebkitBackdropFilter: 'blur(32px) saturate(160%)',
                    boxShadow: '0 20px 48px rgba(0, 0, 0, 0.7), inset 0 1px 0 rgba(255, 255, 255, 0.12)'
                  }}
                >
                  {/* Card Header: Icon, Titles & Status Badge */}
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex items-center gap-3 min-w-0">
                      <div className="w-9 h-9 rounded-xl bg-white/[0.04] border border-white/[0.08] flex items-center justify-center text-white shrink-0">
                        {pendingInterrupt.interrupt_type === 'mutating_tool' ? (
                          <svg className="w-4 h-4 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}>
                            <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m0-10.03A11.95 11.95 0 0112 2.944a11.95 11.95 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016zM12 15.75h.007v.008H12v-.008z" />
                          </svg>
                        ) : (
                          <svg className="w-4 h-4 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}>
                            <path strokeLinecap="round" strokeLinejoin="round" d="M13.5 16.875h3.375m0 0h3.375m-3.375 0V13.5m0 3.375v3.375M6 10.5h2.25a2.25 2.25 0 002.25-2.25V6a2.25 2.25 0 00-2.25-2.25H6A2.25 2.25 0 003.75 6v2.25A2.25 2.25 0 006 10.5zm0 9.75h2.25A2.25 2.25 0 0010.5 18v-2.25a2.25 2.25 0 00-2.25-2.25H6a2.25 2.25 0 00-2.25 2.25V18A2.25 2.25 0 006 20.25zm9.75-9.75H18a2.25 2.25 0 002.25-2.25V6A2.25 2.25 0 0018 3.75h-2.25A2.25 2.25 0 0013.5 6v2.25a2.25 2.25 0 002.25 2.25z" />
                          </svg>
                        )}
                      </div>
                      <div className="min-w-0 flex-1">
                        <h4 className="text-xs sm:text-sm font-semibold text-white tracking-wide font-mono truncate">
                          {pendingInterrupt.interrupt_type === 'mutating_tool'
                            ? `Execute: ${pendingInterrupt.tool_name || pendingInterrupt.display_name}`
                            : (pendingInterrupt.display_name || 'External MCP Tool')}
                        </h4>
                        <p className="text-[11px] text-slate-400 font-sans leading-snug mt-0.5 truncate">
                          {pendingInterrupt.description || (
                            pendingInterrupt.interrupt_type === 'mutating_tool'
                              ? 'Mutating operation on external resource/environment'
                              : 'Extension capability required to answer query'
                          )}
                        </p>
                      </div>
                    </div>
                    <span className="text-[10px] font-mono px-2.5 py-0.5 rounded-full bg-white/[0.05] border border-white/[0.08] text-slate-300 font-normal shrink-0 flex items-center gap-1.5">
                      <span className="w-1.5 h-1.5 rounded-full bg-white shadow-[0_0_6px_rgba(255,255,255,0.7)]" />
                      {pendingInterrupt.interrupt_type === 'mutating_tool' ? 'Mutating Action' : 'Approval Required'}
                    </span>
                  </div>

                  {/* Proposed Parameters Preview for Mutating Tools */}
                  {pendingInterrupt.interrupt_type === 'mutating_tool' && pendingInterrupt.proposed_args && Object.keys(pendingInterrupt.proposed_args).length > 0 && (
                    <div className="rounded-xl bg-black/70 border border-white/[0.08] overflow-hidden text-xs font-mono">
                      <div className="flex items-center justify-between px-3.5 py-2 bg-white/[0.03] border-b border-white/[0.06] text-[10px] text-slate-400 uppercase tracking-widest font-mono font-semibold">
                        <span className="flex items-center gap-1.5 text-white/90">
                          <svg className="w-3.5 h-3.5 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}>
                            <path strokeLinecap="round" strokeLinejoin="round" d="M17.25 6.75L22.5 12l-5.25 5.25m-10.5 0L1.5 12l5.25-5.25m7.5-3l-4.5 16.5" />
                          </svg>
                          Proposed Parameters
                        </span>
                        <span className="text-[9px] text-slate-500 lowercase font-mono font-normal">
                          {Object.keys(pendingInterrupt.proposed_args).length} argument(s)
                        </span>
                      </div>
                      <pre className="p-3.5 text-[11px] font-mono text-slate-200 overflow-x-auto whitespace-pre-wrap leading-relaxed max-h-36 selection:bg-white/20">
                        {JSON.stringify(pendingInterrupt.proposed_args, null, 2)}
                      </pre>
                    </div>
                  )}

                  {/* Clarification prompt message */}
                  <p className="text-xs sm:text-sm text-slate-300 leading-relaxed font-sans border-t border-white/[0.06] pt-3">
                    {pendingInterrupt.message || (
                      pendingInterrupt.interrupt_type === 'mutating_tool'
                        ? 'MoKa needs authorization before applying this mutation to ensure data safety.'
                        : 'MoKa needs permission to proceed with this request.'
                    )}
                  </p>

                  {/* Action Buttons: Pure Black & White matching Chat History */}
                  <div className="flex items-center justify-end gap-2.5 pt-1">
                    <button
                      type="button"
                      onClick={() => handleResolveInterrupt(false)}
                      disabled={isResuming}
                      className="px-4 py-2 rounded-xl bg-white/[0.04] hover:bg-white/[0.08] border border-white/[0.08] hover:border-white/20 text-slate-300 hover:text-white font-mono text-xs tracking-wider uppercase transition-all cursor-pointer active:scale-95 disabled:opacity-40 flex items-center gap-1.5"
                    >
                      <svg className="w-3.5 h-3.5 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                      </svg>
                      {pendingInterrupt.interrupt_type === 'mutating_tool' ? 'Decline Action' : 'Cancel'}
                    </button>
                    <button
                      type="button"
                      onClick={() => handleResolveInterrupt(true)}
                      disabled={isResuming}
                      className="px-4 py-2 rounded-xl bg-white hover:bg-white/90 text-black font-semibold text-xs tracking-wider uppercase font-mono transition-all duration-200 cursor-pointer shadow-[0_4px_16px_rgba(255,255,255,0.15)] active:scale-[0.98] flex items-center gap-2 disabled:opacity-40"
                    >
                      {isResuming ? (
                        <>
                          <span className="w-3.5 h-3.5 border-2 border-black/30 border-t-black rounded-full animate-spin" />
                          <span>Authorizing...</span>
                        </>
                      ) : (
                        <>
                          <svg className="w-3.5 h-3.5 text-black" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                            <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
                          </svg>
                          <span>
                            {pendingInterrupt.interrupt_type === 'mutating_tool' ? 'Approve & Execute' : 'Add Tool & Continue'}
                          </span>
                        </>
                      )}
                    </button>
                  </div>
                </div>
              </div>
            )}

            {/* Thinking indicator bubble with cognitive telemetry (only shown during routing/thinking phase before text tokens) */}
            {isMokaThinking && (
              <div className="flex flex-col self-start items-start max-w-[95%] sm:max-w-[85%]">
                <span className="text-[10px] text-slate-400 font-mono font-semibold uppercase tracking-wider mb-1.5 px-1 flex items-center gap-1.5">
                  <span className="w-1.5 h-1.5 rounded-full bg-[var(--brand-primary)]" />
                  MoKa
                </span>
                <CognitiveTelemetryCard telemetry={cognitiveTelemetry} />
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>
        </div>
      )}

      {/* Sliding Input Box Container - 100% dead center in viewport */}
      <div
        className={`absolute left-1/2 -translate-x-1/2 w-full px-6 transition-all duration-700 ease-in-out z-20 !overflow-visible ${
          isConversationStarted ? 'bottom-6 max-w-2xl' : 'bottom-10 max-w-xl'
        }`}
      >
        <div className="relative w-full !overflow-visible">
          {/* Active Document Upload / Ingestion Status Badge */}
          {activeUpload && (
            <div className="mb-3 w-full bg-[var(--brand-card-bg)]/95 border border-[var(--brand-card-border)] backdrop-blur-xl rounded-2xl p-3 shadow-2xl flex items-center justify-between gap-3 animate-in fade-in slide-in-from-bottom-2 duration-300">
              <div className="flex items-center gap-3 min-w-0 flex-1">
                <div className="w-9 h-9 rounded-xl bg-[var(--brand-primary)]/15 text-[var(--brand-primary)] flex items-center justify-center flex-shrink-0">
                  {activeUpload.status === 'completed' ? (
                    <svg className="w-5 h-5 text-emerald-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
                    </svg>
                  ) : activeUpload.status === 'failed' ? (
                    <svg className="w-5 h-5 text-rose-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m9-.75a9 9 0 11-18 0 9 9 0 0118 0zm-9 3.75h.008v.008H12v-.008z" />
                    </svg>
                  ) : (
                    <svg className="w-5 h-5 animate-spin text-[var(--brand-primary)]" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0l3.181 3.183a8.25 8.25 0 0013.803-3.7M4.031 9.865a8.25 8.25 0 0113.803-3.7l3.181 3.182m0-4.991v4.99" />
                    </svg>
                  )}
                </div>
                <div className="min-w-0 flex-1">
                  <div className="flex items-center justify-between gap-2 mb-1">
                    <span className="text-xs font-semibold text-white truncate font-sans">
                      {activeUpload.file.name}
                    </span>
                    <span className="text-[11px] font-mono text-slate-400 flex-shrink-0">
                      {activeUpload.status === 'completed'
                        ? (activeUpload.result?.chunks_processed || activeUpload.result?.upserted_count
                            ? `Ready (${activeUpload.result.chunks_processed || activeUpload.result.upserted_count} chunks)`
                            : 'Ready for Q&A')
                        : activeUpload.status === 'failed'
                        ? 'Failed'
                        : `${activeUpload.progress}%`}
                    </span>
                  </div>
                  {activeUpload.status === 'failed' ? (
                    <p className="text-[11px] text-rose-400 truncate font-sans">
                      {activeUpload.error || 'Failed to process document'}
                    </p>
                  ) : (
                    <div className="w-full bg-white/10 rounded-full h-1.5 overflow-hidden">
                      <div
                        className={`h-full transition-all duration-500 rounded-full ${
                          activeUpload.status === 'completed'
                            ? 'bg-emerald-400'
                            : 'bg-[var(--brand-primary)]'
                        }`}
                        style={{ width: `${activeUpload.progress}%` }}
                      />
                    </div>
                  )}
                </div>
              </div>
              <div className="flex items-center gap-2 flex-shrink-0">
                {activeUpload.status === 'completed' && (
                  <button
                    type="button"
                    aria-pressed={isDocFocusEnabled}
                    onClick={() => setIsDocFocusEnabled(prev => !prev)}
                    className={`px-2.5 py-1 rounded-full text-[11px] font-medium border transition-all flex items-center gap-1.5 cursor-pointer ${
                      isDocFocusEnabled
                        ? 'border-[var(--brand-primary)]/45 bg-[var(--brand-primary)]/15 text-[var(--brand-primary)] shadow-sm'
                        : 'border-white/10 bg-white/5 text-slate-300 hover:text-white hover:border-white/25'
                    }`}
                    title={
                      isDocFocusEnabled
                        ? 'PDF Focus ON: Messages bypass tools and query this uploaded document directly'
                        : 'PDF Focus OFF: Normal router decides between tools and document Q&A'
                    }
                  >
                    <span
                      className={`w-1.5 h-1.5 rounded-full ${
                        isDocFocusEnabled ? 'bg-emerald-400' : 'bg-slate-500'
                      }`}
                    />
                    <span>{isDocFocusEnabled ? 'PDF Focus: ON' : 'PDF Focus: OFF'}</span>
                  </button>
                )}
                <button
                  type="button"
                  onClick={() => {
                    setActiveUpload(null);
                    setIsDocFocusEnabled(false);
                  }}
                  className="text-slate-400 hover:text-white p-1 rounded-lg hover:bg-white/10 transition-colors flex-shrink-0"
                  title="Dismiss"
                >
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>
            </div>
          )}

          <BorderBeam
            size="pulse-inner"
            colorVariant="mono"
            active={isInputFocused}
            borderRadius={24}
            className="w-full rounded-3xl !overflow-visible"
            style={{ overflow: 'visible' }}
          >
            <div
              className="w-full flex items-center rounded-3xl p-2.5 shadow-[0_20px_50px_rgba(0,0,0,0.8)] bg-[var(--brand-card-bg)] border border-[var(--brand-card-border)] backdrop-blur-2xl transition-all duration-300 gap-3 !overflow-visible cursor-text"
              onClick={(e) => {
                if (!(e.target as HTMLElement).closest('button')) {
                  inputRef.current?.focus();
                }
              }}
            >
              {/* Liquid Gooey Menu on the left side of the mute button */}
              <div className="relative w-10 h-10 flex-shrink-0 z-30">
                <Liquid fill="#202020" className="relative w-10 h-10">
                  <Liquid.Item
                    x={open ? -58 : 0}
                    y={0}
                    transition={{ duration: 500, ease: 'cubic-bezier(0.16, 1, 0.3, 1)' }}
                    className="absolute top-0 left-0"
                    style={{ position: 'absolute', top: 0, left: 0, pointerEvents: open ? 'auto' : 'none' }}
                  >
                    <button
                      id="model-mode-toggle-btn"
                      className="round-btn"
                      type="button"
                      onClick={(e) => {
                        e.stopPropagation();
                        handleToggleModelMode(modelMode === 'local' ? 'cloud' : 'local');
                      }}
                      title={modelMode === 'cloud' ? 'Cloud Mode (Azure Phi-4) · Click to switch to Local (Ollama)' : 'Local Mode (Ollama) · Click to switch to Cloud (Azure Phi-4)'}
                      aria-label={modelMode === 'cloud' ? 'Cloud Mode (Azure Phi-4)' : 'Local Mode (Ollama)'}
                    >
                      {modelMode === 'local' ? (
                        <svg className="w-4 h-4 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                          <rect x="4" y="4" width="16" height="16" rx="2" />
                          <path d="M9 9h6v6H9z" />
                          <path strokeLinecap="round" d="M9 1v3M15 1v3M9 20v3M15 20v3M20 9h3M20 15h3M1 9h3M1 15h3" />
                        </svg>
                      ) : (
                        <svg className="w-4 h-4 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                          <path strokeLinecap="round" strokeLinejoin="round" d="M17.5 19H9a7 7 0 1 1 6.71-9h1.79a4.5 4.5 0 1 1 0 9Z" />
                        </svg>
                      )}
                    </button>
                  </Liquid.Item>
                  <Liquid.Item
                    x={open ? -34 : 0}
                    y={open ? -48 : 0}
                    transition={{ duration: 500, ease: 'cubic-bezier(0.16, 1, 0.3, 1)' }}
                    delay={40}
                    className="absolute top-0 left-0"
                    style={{ position: 'absolute', top: 0, left: 0, pointerEvents: open ? 'auto' : 'none' }}
                  >
                    <button
                      className="round-btn"
                      type="button"
                      title="Upload Document for Grounded RAG"
                      aria-label="Upload Document"
                      onClick={(e) => {
                        e.stopPropagation();
                        fileInputRef.current?.click();
                        setOpen(false);
                      }}
                    >
                      <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m2.25 0H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" />
                      </svg>
                    </button>
                  </Liquid.Item>
                  <Liquid.Item
                    x={open ? 22 : 0}
                    y={open ? -56 : 0}
                    transition={{ duration: 500, ease: 'cubic-bezier(0.16, 1, 0.3, 1)' }}
                    delay={80}
                    className="absolute top-0 left-0"
                    style={{ position: 'absolute', top: 0, left: 0, pointerEvents: open ? 'auto' : 'none' }}
                  >
                    <button className="round-btn" type="button" title="Image" aria-label="Image">
                      <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M2.25 15.75l5.159-5.159a2.25 2.25 0 013.182 0l5.159 5.159m-1.5-1.5l1.409-1.409a2.25 2.25 0 013.182 0l2.909 2.909m-18 3.75h16.5a1.5 1.5 0 001.5-1.5V6a1.5 1.5 0 00-1.5-1.5H3.75A1.5 1.5 0 002.25 6v12a1.5 1.5 0 001.5 1.5zm10.5-11.25h.008v.008h-.008V8.25zm.375 0a.375.375 0 11-.75 0 .375.375 0 01.75 0z" />
                      </svg>
                    </button>
                  </Liquid.Item>
                  <Liquid.Item
                    className="absolute top-0 left-0 z-10"
                    style={{ position: 'absolute', top: 0, left: 0 }}
                  >
                    <button
                      className={`round-btn transition-transform duration-300 ${open ? 'rotate-45' : ''}`}
                      type="button"
                      onClick={() => setOpen((prev) => !prev)}
                      aria-label="Toggle menu"
                    >
                      +
                    </button>
                  </Liquid.Item>
                </Liquid>
              </div>

              <button
                onClick={handleToggleMute}
                className={`w-10 h-10 rounded-2xl border transition-all duration-300 cursor-pointer flex items-center justify-center flex-shrink-0 ${isMuted
                  ? 'bg-[#202020] border-white/10 text-white hover:bg-[#2c2c2c]'
                  : 'theme-icon-box text-[var(--brand-primary)]'
                  }`}
                title={isMuted ? "Unmute speech output" : (isCozmoConnected ? "Mute Cozmo speaker" : "Mute laptop speech output")}
                aria-label={isMuted ? "Unmute speech output" : (isCozmoConnected ? "Mute Cozmo speaker" : "Mute laptop speech output")}
              >
                {isMuted ? (
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M17.25 9.75L19.5 12m0 0l2.25 2.25M19.5 12l2.25-2.25M19.5 12l-2.25 2.25m-10.5-6L4.5 9H1.5v6h3l4.5 3.75V5.25z" />
                  </svg>
                ) : (
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M19.114 5.636a9 9 0 010 12.728M16.463 8.288a5.25 5.25 0 010 7.424M6.75 8.25l4.72-4.72a.75.75 0 011.28.53v15.88a.75.75 0 01-1.28.53l-4.72-4.72H4.51c-.88 0-1.704-.507-1.938-1.354A9.01 9.01 0 012.25 12c0-.83.112-1.633.322-2.396C2.806 8.756 3.63 8.25 4.51 8.25H6.75z" />
                  </svg>
                )}
              </button>

              {/* Hidden Document File Picker for Grounded RAG */}
              <input
                ref={fileInputRef}
                type="file"
                accept=".pdf,.docx,.doc,.txt,.md"
                className="hidden"
                style={{ display: 'none' }}
                onChange={(e) => {
                  const file = e.target.files?.[0];
                  if (file) {
                    handleUploadFile(file);
                    e.target.value = '';
                  }
                }}
              />

              <input
                ref={inputRef}
                autoFocus
                type="text"
                value={inputText}
                onChange={(e) => {
                  const val = e.target.value;
                  if (val.length !== prevInputLengthRef.current) {
                    prevInputLengthRef.current = val.length;
                    triggerTypingPulse();
                  }
                  setInputText(val);
                }}
                onKeyDown={handleKeyDown}
                onFocus={() => setIsInputFocused(true)}
                onBlur={() => setIsInputFocused(false)}
                placeholder="Message MoKa..."
                className="flex-1 bg-transparent border-0 outline-none text-white text-base px-2 placeholder-slate-400 font-sans min-w-0"
              />

              <button
                onClick={() => {
                  handleSendMessage();
                  inputRef.current?.focus();
                }}
                disabled={!inputText.trim()}
                className="w-10 h-10 rounded-2xl flex items-center justify-center transition-all disabled:opacity-20 disabled:pointer-events-none cursor-pointer active:scale-95 flex-shrink-0 text-black font-bold"
                style={{
                  background: 'var(--brand-primary)',
                  boxShadow: '0 0 20px var(--brand-glow)'
                }}
                aria-label="Send"
              >
                <svg className="w-4 h-4 text-black" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M14 5l7 7m0 0l-7 7m7-7H3" />
                </svg>
              </button>
            </div>
          </BorderBeam>
        </div>
      </div>
    </div>
  );
};

export default ChatInterface;
