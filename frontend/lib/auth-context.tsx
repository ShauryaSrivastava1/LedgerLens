"use client";

import { createContext, useContext, useEffect, useState } from "react";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const TOKEN_STORAGE_KEY = "equity_platform_token";

interface CurrentUser {
  id: string;
  email: string;
  full_name: string | null;
}

interface AuthContextValue {
  token: string | null;
  user: CurrentUser | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, fullName?: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [token, setToken] = useState<string | null>(null);
  const [user, setUser] = useState<CurrentUser | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const stored = localStorage.getItem(TOKEN_STORAGE_KEY);
    if (stored) {
      setToken(stored);
      fetchMe(stored).finally(() => setLoading(false));
    } else {
      setLoading(false);
    }
  }, []);

  async function fetchMe(t: string) {
    try {
      const res = await fetch(`${API_BASE_URL}/auth/me`, {
        headers: { Authorization: `Bearer ${t}` },
      });
      if (res.ok) {
        setUser(await res.json());
      } else {
        localStorage.removeItem(TOKEN_STORAGE_KEY);
        setToken(null);
      }
    } catch {
      // network error — leave token in place, user can retry
    }
  }

  async function authenticate(path: "login" | "register", body: BodyInit, isForm: boolean) {
    const res = await fetch(`${API_BASE_URL}/auth/${path}`, {
      method: "POST",
      headers: isForm ? undefined : { "Content-Type": "application/json" },
      body,
    });
    if (!res.ok) {
      const errBody = await res.json().catch(() => ({}));
      throw new Error(errBody.detail || "Authentication failed");
    }
    const data = await res.json();
    localStorage.setItem(TOKEN_STORAGE_KEY, data.access_token);
    setToken(data.access_token);
    await fetchMe(data.access_token);
  }

  async function login(email: string, password: string) {
    const form = new URLSearchParams();
    form.set("username", email);
    form.set("password", password);
    await authenticate("login", form, true);
  }

  async function register(email: string, password: string, fullName?: string) {
    await authenticate(
      "register",
      JSON.stringify({ email, password, full_name: fullName || undefined }),
      false
    );
  }

  function logout() {
    localStorage.removeItem(TOKEN_STORAGE_KEY);
    setToken(null);
    setUser(null);
  }

  return (
    <AuthContext.Provider value={{ token, user, loading, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
