import type { ReactNode } from "react";
import { createContext, useContext, useEffect, useMemo, useState } from "react";

import {
  clearSession,
  getCurrentDriverProfile,
  getStoredToken,
  getStoredUser,
  loginDriver,
  markCurrentDriverOffline,
  registerDriver,
  sendDriverPresenceHeartbeat,
} from "../api/auth";
import type {
  AuthSessionResponse,
  AuthUser,
  DriverLoginPayload,
  DriverRegistrationPayload,
} from "@shared/types/auth";

type SessionContextValue = {
  isLoading: boolean;
  token: string | null;
  user: AuthUser | null;
  isSignedIn: boolean;
  applySession: (session: AuthSessionResponse) => void;
  setUser: (user: AuthUser | null) => void;
  signIn: (payload: DriverLoginPayload) => Promise<AuthSessionResponse>;
  signUp: (payload: DriverRegistrationPayload) => Promise<AuthSessionResponse | { success: true }>;
  signOut: () => void;
};

const SessionContext = createContext<SessionContextValue | null>(null);

export function DriverSessionProvider({ children }: { children: ReactNode }) {
  const [isLoading, setIsLoading] = useState(true);
  const [token, setToken] = useState<string | null>(null);
  const [user, setUser] = useState<AuthUser | null>(null);

  useEffect(() => {
    const storedToken = getStoredToken();
    const storedUser = getStoredUser();
    if (!storedToken) {
      setIsLoading(false);
      return;
    }
    setToken(storedToken);
    setUser(storedUser);
    void getCurrentDriverProfile()
      .then((currentUser) => setUser(currentUser))
      .catch(() => {
        clearSession();
        setToken(null);
        setUser(null);
      })
      .finally(() => setIsLoading(false));
  }, []);

  useEffect(() => {
    if (!token) {
      return;
    }

    void sendDriverPresenceHeartbeat();
    const heartbeatId = window.setInterval(() => {
      void sendDriverPresenceHeartbeat();
    }, 15_000);

    return () => window.clearInterval(heartbeatId);
  }, [token]);

  function applySession(session: AuthSessionResponse) {
    setToken(session.accessToken);
    setUser(session.user);
  }

  async function signIn(payload: DriverLoginPayload) {
    const auth = await loginDriver(payload);
    applySession(auth);
    return auth;
  }

  async function signUp(payload: DriverRegistrationPayload) {
    const response = await registerDriver(payload);
    if ("accessToken" in response) {
      applySession(response);
    }
    return response;
  }

  function signOut() {
    void markCurrentDriverOffline();
    clearSession();
    setToken(null);
    setUser(null);
  }

  const value = useMemo(
    () => ({
      isLoading,
      token,
      user,
      isSignedIn: Boolean(token),
      applySession,
      setUser,
      signIn,
      signUp,
      signOut,
    }),
    [isLoading, token, user],
  );

  return <SessionContext.Provider value={value}>{children}</SessionContext.Provider>;
}

export function useDriverSession() {
  const context = useContext(SessionContext);
  if (!context) {
    throw new Error("useDriverSession must be used inside DriverSessionProvider");
  }
  return context;
}
