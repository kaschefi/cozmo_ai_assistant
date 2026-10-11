export interface Message {
  id: string;
  sender: 'user' | 'moka';
  text: string;
  timestamp: string;
}

export interface ChatSession {
  id: string;
  title: string;
  createdAt: number;
  updatedAt: number;
  messages: Message[];
  modelMode?: 'local' | 'cloud';
}

const STORAGE_KEY = 'moka_chat_sessions';
const ACTIVE_SESSION_KEY = 'moka_active_session_id';
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

function getHeaders(token?: string): Record<string, string> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  };
  if (token) {
    headers['X-Moka-Token'] = token;
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
    const res = await fetch(`${API_BASE_URL}/api/history`, {
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
    await fetch(`${API_BASE_URL}/api/history`, {
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
    await fetch(`${API_BASE_URL}/api/history/${sessionId}`, {
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
    await fetch(`${API_BASE_URL}/api/history/${sessionId}`, {
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
    await fetch(`${API_BASE_URL}/api/history`, {
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
    const res = await fetch(`${API_BASE_URL}/api/history/sync-langsmith`, {
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
 * Saves the active session ID to localStorage.
 */
export function setActiveSessionId(id: string): void {
  try {
    localStorage.setItem(ACTIVE_SESSION_KEY, id);
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
