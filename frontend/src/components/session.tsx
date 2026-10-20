"use client";

import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from "react";

import { ApiError, getMe, getToken, setToken, type Session, type Usage, type User } from "../lib/api";

type SessionValue = {
  user: User | null;
  /** true as soon as a token exists, before the server confirms it (no logged-out flash on reload) */
  signedIn: boolean;
  usage: Usage | null;
  loading: boolean;
  signIn: (session: Session) => Promise<void>;
  signOut: () => void;
  refresh: () => Promise<void>;
};

const SessionContext = createContext<SessionValue | null>(null);

export function SessionProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [usage, setUsage] = useState<Usage | null>(null);
  const [loading, setLoading] = useState(true);
  const [hasToken, setHasToken] = useState(false);

  const refresh = useCallback(async () => {
    setHasToken(!!getToken());
    if (!getToken()) {
      setUser(null);
      setUsage(null);
      setLoading(false);
      return;
    }
    try {
      const me = await getMe();
      setUser(me.user);
      setUsage(me.usage);
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        setToken(null);
        setHasToken(false);
      }
      setUser(null);
      setUsage(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const signIn = useCallback(async (session: Session) => {
    setToken(session.token);
    setHasToken(true);
    setUser(session.user);
    await refresh();
  }, [refresh]);

  const signOut = useCallback(() => {
    setToken(null);
    setHasToken(false);
    setUser(null);
    setUsage(null);
  }, []);

  return (
    <SessionContext.Provider value={{ user, signedIn: !!user || (loading && hasToken), usage, loading, signIn, signOut, refresh }}>{children}</SessionContext.Provider>
  );
}

export function useSession(): SessionValue {
  const value = useContext(SessionContext);
  if (!value) throw new Error("useSession must be used inside <SessionProvider>");
  return value;
}