export interface MessageTelemetry {
  elapsedSeconds?: number;
  tool?: string;
  provider?: string;
  steps?: string[];
}

export interface Message {
  id: string;
  sender: 'user' | 'moka';
  text: string;
  timestamp: string;
  telemetry?: MessageTelemetry;
}

export interface ChatSession {
  id: string;
  title: string;
  createdAt: number;
  updatedAt: number;
  messages: Message[];
  modelMode?: 'local' | 'cloud';
}

import { getApiBaseUrl, getMokaToken } from '../../../shared/utils';

const STORAGE_KEY = 'moka_chat_sessions';
const ACTIVE_SESSION_KEY = 'moka_active_session_id';

function getHeaders(token?: string): Record<string, string> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  };
  const activeToken = token || getMokaToken();
  if (activeToken) {
    headers['X-Moka-Token'] = activeToken;
  }
  return headers;
}

export const RETENTION_DAYS = 30;
export const RETENTION_MS = RETENTION_DAYS * 24 * 60 * 60 * 1000;

/**
 * Loads all saved chat sessions from localStorage, sorted by most recently updated,
 * and automatically prunes conversations older than 30 days (1 month).
 */
export function loadChatSessions(): ChatSession[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    if (Array.isArray(parsed)) {
      const now = Date.now();
      const cutoff = now - RETENTION_MS;
      // Auto-prune conversations older than 30 days
      const valid = parsed.filter(s => (s.updatedAt || s.createdAt || 0) >= cutoff);
      if (valid.length !== parsed.length) {
        saveChatSessions(valid);
      }
      return valid.sort((a, b) => (b.updatedAt || 0) - (a.updatedAt || 0));
    }
    return [];
  } catch (err) {
    console.error('Failed to load chat sessions from localStorage:', err);
    return [];
  }
}

/**
 * Persists all chat sessions to localStorage.
 */
export function saveChatSessions(sessions: ChatSession[]): void {
  try {
    const now = Date.now();
    const cutoff = now - RETENTION_MS;
    const valid = sessions.filter(s => (s.updatedAt || s.createdAt || 0) >= cutoff);
    localStorage.setItem(STORAGE_KEY, JSON.stringify(valid));
  } catch (err) {
    console.error('Failed to save chat sessions to localStorage:', err);
  }
}

/**
 * Fetches all persistent chat sessions from the database API.
 * Automatically filters out any conversations older than 30 days.
 */
export async function fetchChatHistoryFromApi(token?: string): Promise<ChatSession[]> {
  try {
    const res = await fetch(`${getApiBaseUrl()}/api/history`, {
      headers: getHeaders(token),
    });
    if (!res.ok) {
      throw new Error(`Failed to fetch history: ${res.status}`);
    }
    const data = await res.json();
    if (data.status === 'success' && Array.isArray(data.sessions)) {
      const now = Date.now();
      const cutoff = now - RETENTION_MS;
      const validSessions: ChatSession[] = data.sessions.filter(
        (s: ChatSession) => (s.updatedAt || s.createdAt || 0) >= cutoff
      );
      saveChatSessions(validSessions);
      return validSessions;
    }
  } catch (err) {
    console.warn('[ChatHistory] Backend DB history fetch notice:', err);
  }
  return loadChatSessions();
}

/**
 * Asynchronously syncs an updated session to the database.
 */
export async function saveChatSessionToApi(session: ChatSession, token?: string): Promise<void> {
  try {
    await fetch(`${getApiBaseUrl()}/api/history`, {
      method: 'POST',
      headers: getHeaders(token),
      body: JSON.stringify(session),
    });
  } catch (err) {
    console.warn('[ChatHistory] Failed to sync session to backend DB:', err);
  }
}

/**
 * Renames a session in the persistent database.
 */
export async function renameChatSessionInApi(sessionId: string, newTitle: string, token?: string): Promise<void> {
  try {
    await fetch(`${getApiBaseUrl()}/api/history/${sessionId}`, {
      method: 'PATCH',
      headers: getHeaders(token),
      body: JSON.stringify({ title: newTitle }),
    });
  } catch (err) {
    console.warn('[ChatHistory] Failed to rename session in backend DB:', err);
  }
}

/**
 * Deletes a session in the persistent database.
 */
export async function deleteChatSessionInApi(sessionId: string, token?: string): Promise<void> {
  try {
    await fetch(`${getApiBaseUrl()}/api/history/${sessionId}`, {
      method: 'DELETE',
      headers: getHeaders(token),
    });
  } catch (err) {
    console.warn('[ChatHistory] Failed to delete session from backend DB:', err);
  }
}

/**
 * Clears all sessions in the persistent database.
 */
export async function clearAllChatSessionsInApi(token?: string): Promise<void> {
  try {
    await fetch(`${getApiBaseUrl()}/api/history`, {
      method: 'DELETE',
      headers: getHeaders(token),
    });
  } catch (err) {
    console.warn('[ChatHistory] Failed to clear history from backend DB:', err);
  }
}

/**
 * Queries LangSmith directly via backend to import historical runs.
 */
export async function syncHistoryFromLangSmith(token?: string): Promise<{ syncedCount: number; sessions: ChatSession[] }> {
  try {
    const res = await fetch(`${getApiBaseUrl()}/api/history/sync-langsmith`, {
      method: 'POST',
      headers: getHeaders(token),
    });
    if (!res.ok) {
      throw new Error(`Failed to sync from LangSmith: ${res.status}`);
    }
    const data = await res.json();
    if (data.status === 'success') {
      const sessions = data.sessions || [];
      saveChatSessions(sessions);
      return {
        syncedCount: data.synced_count || 0,
        sessions,
      };
    }
  } catch (err) {
    console.error('[ChatHistory] LangSmith sync failed:', err);
  }
  return { syncedCount: 0, sessions: loadChatSessions() };
}

const TAB_ACTIVE_SESSION_KEY = 'moka_tab_active_session_id';

/**
 * Checks if the current page load is an actual browser page reload (F5 / Refresh).
 */
export function isBrowserReload(): boolean {
  try {
    const navEntries = performance.getEntriesByType('navigation');
    if (navEntries && navEntries.length > 0) {
      return (navEntries[0] as PerformanceNavigationTiming).type === 'reload';
    }
    // Fallback for older browsers
    // @ts-ignore
    return window.performance?.navigation?.type === 1;
  } catch {
    return false;
  }
}

/**
 * Gets the active session ID from localStorage.
 */
export function getActiveSessionId(): string | null {
  try {
    return localStorage.getItem(ACTIVE_SESSION_KEY);
  } catch {
    return null;
  }
}

/**
 * Determines whether the chat interface should restore an ongoing conversation or start fresh.
 * - On first visit or navigation from landing: returns null (initiates a fresh new chat).
 * - On browser reload of the chat page (F5): returns the active session ID to keep the conversation intact.
 */
export function getSessionToRestoreOnMount(): string | null {
  try {
    if (!isBrowserReload()) {
      return null;
    }
    const tabActiveId = sessionStorage.getItem(TAB_ACTIVE_SESSION_KEY);
    if (tabActiveId) {
      return tabActiveId;
    }
    return getActiveSessionId();
  } catch {
    return null;
  }
}

/**
 * Saves the active session ID for both the current browser tab and persistent storage.
 */
export function setTabActiveSessionId(id: string): void {
  try {
    sessionStorage.setItem(TAB_ACTIVE_SESSION_KEY, id);
    localStorage.setItem(ACTIVE_SESSION_KEY, id);
  } catch (err) {
    console.error('Failed to set tab active session ID:', err);
  }
}

/**
 * Clears the active chat session from the current tab (e.g. when returning to landing page).
 */
export function clearTabActiveSession(): void {
  try {
    sessionStorage.removeItem(TAB_ACTIVE_SESSION_KEY);
  } catch {
    // Ignore storage quota
  }
}

/**
 * Saves the active session ID to localStorage.
 */
export function setActiveSessionId(id: string): void {
  try {
    localStorage.setItem(ACTIVE_SESSION_KEY, id);
    sessionStorage.setItem(TAB_ACTIVE_SESSION_KEY, id);
  } catch (err) {
    console.error('Failed to set active session ID in localStorage:', err);
  }
}

/**
 * Generates a unique session ID.
 */
export function generateSessionId(): string {
  return 'web_' + Date.now().toString(36) + '_' + Math.random().toString(36).slice(2, 7);
}

/**
 * Generates a clean human-readable title from the first message text.
 */
export function generateSessionTitle(firstMessageText: string): string {
  const clean = firstMessageText.trim().replace(/\s+/g, ' ');
  if (!clean) return 'New Conversation';
  if (clean.length <= 36) return clean;
  return clean.slice(0, 36).trim() + '...';
}

/**
 * Formats a timestamp into a human-friendly relative or date string.
 */
export function formatSessionTime(timestamp: number): string {
  if (!timestamp) return '';
  const now = Date.now();
  const diffMs = now - timestamp;
  const diffMinutes = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMinutes / 60);
  const diffDays = Math.floor(diffHours / 24);

  if (diffMinutes < 1) return 'Just now';
  if (diffMinutes < 60) return `${diffMinutes}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  if (diffDays === 1) return 'Yesterday';
  if (diffDays < 7) return `${diffDays}d ago`;

  const date = new Date(timestamp);
  return date.toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
}
