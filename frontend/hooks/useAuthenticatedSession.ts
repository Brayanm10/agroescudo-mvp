"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { ApiError } from "@/lib/api";
import { LatestRequest } from "@/lib/latest-request";
import { clearStoredSession, readSessionToken, storeSessionToken } from "@/lib/session";

export function useAuthenticatedSession<T>(loader: (token: string) => Promise<T>) {
  const [token, setToken] = useState<string | null>(null);
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [sessionExpired, setSessionExpired] = useState(false);
  const requests = useRef(new LatestRequest());

  const loadForToken = useCallback(async (currentToken: string) => {
    const sequence = requests.current.begin();
    setLoading(true);
    setError(null);
    try {
      const payload = await loader(currentToken);
      if (!requests.current.isCurrent(sequence)) return;
      setData(payload);
      setSessionExpired(false);
    } catch (err) {
      if (!requests.current.isCurrent(sequence)) return;
      if (err instanceof ApiError && err.status === 401) {
        clearStoredSession();
        setToken(null);
        setData(null);
        setSessionExpired(true);
        return;
      }
      setError(err instanceof Error ? err.message : "No se pudo cargar la API.");
    } finally {
      if (requests.current.isCurrent(sequence)) setLoading(false);
    }
  }, [loader]);

  useEffect(() => {
    const stored = readSessionToken();
    if (!stored) {
      setLoading(false);
      return;
    }
    setToken(stored);
    void loadForToken(stored);
  }, [loadForToken]);

  const refresh = useCallback(async () => {
    if (token) await loadForToken(token);
  }, [loadForToken, token]);

  const authenticate = useCallback(async (accessToken: string) => {
    storeSessionToken(accessToken);
    setToken(accessToken);
    setSessionExpired(false);
    await loadForToken(accessToken);
  }, [loadForToken]);

  const logout = useCallback(() => {
    requests.current.cancelAll();
    clearStoredSession();
    setToken(null);
    setData(null);
    setError(null);
    setSessionExpired(false);
    setLoading(false);
  }, []);

  return {
    token,
    data,
    loading,
    error,
    sessionExpired,
    setError,
    refresh,
    authenticate,
    logout
  };
}
