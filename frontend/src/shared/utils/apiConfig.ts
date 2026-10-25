/**
 * Dynamic API, WebSocket, and Token configuration for local dev and cloud production.
 *
 * Rules:
 * 1. If VITE_API_BASE_URL is explicitly set, use it.
 * 2. In local dev (e.g. Vite dev server on port 5173), default to http://<hostname>:8000.
 * 3. In production (served via Nginx / Azure / custom domain), use window.location.origin
 *    so requests are sent to the same origin, eliminating CORS issues and port mismatches.
 */

const TOKEN_STORAGE_KEY = 'moka_admin_token';

export function getApiBaseUrl(): string {
  if (import.meta.env.VITE_API_BASE_URL) {
    return import.meta.env.VITE_API_BASE_URL.replace(/\/+$/, '');
  }
  if (typeof window !== 'undefined') {
    // Vite dev server runs on port 5173 by default
    if (window.location.port === '5173') {
      const hostname = window.location.hostname || 'localhost';
      return `http://${hostname}:8000`;
    }
    // Production: served on port 80/443 behind Nginx or Azure
    return window.location.origin;
  }
  return 'http://localhost:8000';
}

export function getWsBaseUrl(): string {
  if (import.meta.env.VITE_WS_BASE_URL) {
    return import.meta.env.VITE_WS_BASE_URL.replace(/\/+$/, '');
  }
  const apiBase = getApiBaseUrl();
  // Automatically convert http -> ws and https -> wss
  return apiBase.replace(/^http(s?):/, 'ws$1:');
}

export function getMokaToken(): string {
  if (typeof window !== 'undefined') {
    const saved = localStorage.getItem(TOKEN_STORAGE_KEY);
    if (saved) return saved;
  }
  return import.meta.env.VITE_MOKA_TOKEN || '';
}

export function setMokaToken(token: string): void {
  if (typeof window !== 'undefined') {
    if (token) {
      localStorage.setItem(TOKEN_STORAGE_KEY, token);
    } else {
      localStorage.removeItem(TOKEN_STORAGE_KEY);
    }
  }
}
