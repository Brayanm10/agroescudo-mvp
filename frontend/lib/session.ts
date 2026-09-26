export const SESSION_TOKEN_KEY = "agroescudo_token";

export function readSessionToken() {
  return window.localStorage.getItem(SESSION_TOKEN_KEY);
}

export function storeSessionToken(token: string) {
  window.localStorage.setItem(SESSION_TOKEN_KEY, token);
}

export function clearStoredSession() {
  window.localStorage.removeItem(SESSION_TOKEN_KEY);
  window.sessionStorage.removeItem(SESSION_TOKEN_KEY);
}
