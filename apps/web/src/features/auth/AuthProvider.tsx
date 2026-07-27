import { createContext, useContext, useEffect, useState, type ReactNode } from 'react';

const API_URL = import.meta.env.VITE_API_URL || 'https://lawebcore-production.up.railway.app';

interface User {
  id: string;
  email: string;
  full_name: string | null;
  role: string;
  status: string;
  created_at: string | null;
}

interface AuthContextType {
  user: User | null;
  token: string | null;
  loading: boolean;
  signIn: (email: string, password: string) => Promise<void>;
  signOut: () => Promise<void>;
  signUp: (email: string, password: string, fullName: string) => Promise<void>;
  updatePassword: (currentPassword: string, newPassword: string) => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const stored = localStorage.getItem('laweb_token');
    if (stored) {
      setToken(stored);
      validateToken(stored);
    } else {
      setLoading(false);
    }
  }, []);

  const validateToken = async (t: string) => {
    try {
      const res = await fetch(`${API_URL}/api/v1/auth/me`, {
        headers: { Authorization: `Bearer ${t}` },
      });
      if (res.ok) {
        const data = await res.json();
        setUser(data);
        setToken(t);
      } else {
        localStorage.removeItem('laweb_token');
        setToken(null);
        setUser(null);
      }
    } catch {
      localStorage.removeItem('laweb_token');
      setToken(null);
      setUser(null);
    } finally {
      setLoading(false);
    }
  };

  const signIn = async (email: string, password: string) => {
    const res = await fetch(`${API_URL}/api/v1/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Login failed' }));
      throw new Error(err.detail || 'Login failed');
    }
    const data = await res.json();
    localStorage.setItem('laweb_token', data.access_token);
    setToken(data.access_token);
    setUser({
      id: data.user_id,
      email: data.email,
      full_name: data.full_name,
      role: data.role,
      status: 'active',
      created_at: data.created_at || null,
    });
  };

  const signOut = async () => {
    localStorage.removeItem('laweb_token');
    setToken(null);
    setUser(null);
    window.location.href = '/login';
  };

  const signUp = async (_email: string, _password: string, _fullName: string) => {
    throw new Error('Sign up is not available. Contact your administrator.');
  };

  const updatePassword = async (_currentPassword: string, _newPassword: string) => {
    throw new Error('Password update is not available. Contact your administrator.');
  };

  return (
    <AuthContext.Provider value={{ user, token, loading, signIn, signOut, signUp, updatePassword }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within an AuthProvider');
  return ctx;
}
