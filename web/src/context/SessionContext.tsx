import React, { createContext, useState, useCallback } from 'react';

interface SessionContextType {
  sessionId: string | null;
  provider: string | null;
  model: string | null;
  expiresIn: number | null;
  setSession: (sessionId: string, provider: string, model: string, expiresIn: number) => void;
  clearSession: () => void;
}

export const SessionContext = createContext<SessionContextType>({
  sessionId: null,
  provider: null,
  model: null,
  expiresIn: null,
  setSession: () => {},
  clearSession: () => {},
});

interface SessionProviderProps {
  children: React.ReactNode;
}

export function SessionProvider({ children }: SessionProviderProps) {
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [provider, setProvider] = useState<string | null>(null);
  const [model, setModel] = useState<string | null>(null);
  const [expiresIn, setExpiresIn] = useState<number | null>(null);

  const handleSetSession = useCallback(
    (sid: string, prov: string, mod: string, exp: number) => {
      setSessionId(sid);
      setProvider(prov);
      setModel(mod);
      setExpiresIn(exp);
      sessionStorage.setItem('sessionId', sid);
    },
    []
  );

  const handleClearSession = useCallback(() => {
    setSessionId(null);
    setProvider(null);
    setModel(null);
    setExpiresIn(null);
    sessionStorage.removeItem('sessionId');
  }, []);

  return (
    <SessionContext.Provider
      value={{
        sessionId,
        provider,
        model,
        expiresIn,
        setSession: handleSetSession,
        clearSession: handleClearSession,
      }}
    >
      {children}
    </SessionContext.Provider>
  );
}
