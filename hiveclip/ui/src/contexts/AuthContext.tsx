import { createContext, useContext, useState, useCallback, useEffect, type ReactNode } from "react";
import { api } from "../api/client";

const TOKEN_KEY = "hiveclip.token";

interface User {
  id: string;
  email: string;
  displayName: string | null;
  role: string;
  createdAt: string;
}

interface AuthState {
  user: User | null;
  token: string | null;
  isLoading: boolean;
}

interface AuthContextValue extends AuthState {
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, displayName?: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<AuthState>({
    user: null,
    token: localStorage.getItem(TOKEN_KEY),
    isLoading: true,
  });

  useEffect(() => {
    if (!state.token) {
      setState((s) => ({ ...s, isLoading: false }));
      return;
    }
    api.get<User>("/auth/me")
      .then((user) => setState({ user, token: state.token, isLoading: false }))
      .catch(() => {
        localStorage.removeItem(TOKEN_KEY);
        setState({ user: null, token: null, isLoading: false });
      });
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    const res = await api.post<{ token: string; user: User }>("/auth/login", { email, password });
    localStorage.setItem(TOKEN_KEY, res.token);
    setState({ user: res.user, token: res.token, isLoading: false });
  }, []);

  const register = useCallback(async (email: string, password: string, displayName?: string) => {
    const res = await api.post<{ token: string; user: User }>("/auth/register", { email, password, displayName });
    localStorage.setItem(TOKEN_KEY, res.token);
    setState({ user: res.user, token: res.token, isLoading: false });
  }, []);

  const logout = useCallback(() => {
    localStorage.removeItem(TOKEN_KEY);
    setState({ user: null, token: null, isLoading: false });
  }, []);

  return (
    <AuthContext.Provider value={{ ...state, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
