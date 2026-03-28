import { ReactNode, createContext, useCallback, useContext, useState } from "react";

const TOKEN_KEY = "access_token";

interface JWTPayload {
  sub: string;
  role: string;
  name?: string;
  exp: number;
}

interface AuthUser {
  username: string;
  name: string;
  role: string;
}

interface AuthContextType {
  token: string | null;
  user: AuthUser | null;
  isAdmin: boolean;
  login: (token: string) => void;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | null>(null);

function decodeJWT(token: string): JWTPayload | null {
  try {
    return JSON.parse(atob(token.split(".")[1])) as JWTPayload;
  } catch {
    return null;
  }
}

function readStoredSession(): { token: string; user: AuthUser } | null {
  const token = sessionStorage.getItem(TOKEN_KEY);
  if (!token) return null;
  const payload = decodeJWT(token);
  if (!payload || payload.exp * 1000 < Date.now()) {
    sessionStorage.removeItem(TOKEN_KEY);
    return null;
  }
  return {
    token,
    user: { username: payload.sub, name: payload.name ?? payload.sub, role: payload.role },
  };
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const stored = readStoredSession();
  const [token, setToken] = useState<string | null>(stored?.token ?? null);
  const [user, setUser] = useState<AuthUser | null>(stored?.user ?? null);

  const login = useCallback((newToken: string) => {
    const payload = decodeJWT(newToken);
    if (payload) {
      sessionStorage.setItem(TOKEN_KEY, newToken);
      setToken(newToken);
      setUser({ username: payload.sub, name: payload.name ?? payload.sub, role: payload.role });
    }
  }, []);

  const logout = useCallback(() => {
    sessionStorage.removeItem(TOKEN_KEY);
    setToken(null);
    setUser(null);
  }, []);

  const isAdmin = user?.role === "admin";

  return (
    <AuthContext.Provider value={{ token, user, isAdmin, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuthContext() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuthContext deve ser usado dentro de AuthProvider");
  return ctx;
}
