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

/**
 * Loads all saved chat sessions from localStorage, sorted by most recently updated.
 */
export function loadChatSessions(): ChatSession[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    if (Array.isArray(parsed)) {
      return parsed.sort((a, b) => (b.updatedAt || 0) - (a.updatedAt || 0));
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
    localStorage.setItem(STORAGE_KEY, JSON.stringify(sessions));
  } catch (err) {
    console.error('Failed to save chat sessions to localStorage:', err);
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
