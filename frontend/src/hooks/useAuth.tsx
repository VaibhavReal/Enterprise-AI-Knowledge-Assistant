import { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { User } from '../types';
import { getCurrentUser, loginUser, registerUser } from '../services/api';
import { useNavigate } from 'react-router-dom';

interface AuthContextType {
  user: User | null;
  token: string | null;
  loading: boolean;
  login: (data: any) => Promise<void>;
  register: (data: any) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider = ({ children }: { children: ReactNode }) => {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(localStorage.getItem('token'));
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    const fetchUser = async () => {
      if (token) {
        try {
          const res = await getCurrentUser();
          setUser(res.data);
        } catch (error) {
          console.error('Failed to fetch user, clearing session', error);
          // Inline logout to avoid stale closure dependency on logout function
          localStorage.removeItem('token');
          setToken(null);
          setUser(null);
        }
      }
      setLoading(false);
    };
    fetchUser();
  }, [token]);


  const login = async (data: any) => {
    const res = await loginUser(data);
    const newToken = res.data.access_token;
    localStorage.setItem('token', newToken);
    setToken(newToken);
    const userRes = await getCurrentUser();
    setUser(userRes.data);
    navigate('/dashboard');
  };

  const register = async (data: any) => {
    await registerUser(data);
    await login({ email: data.email, password: data.password });
  };

  const logout = () => {
    localStorage.removeItem('token');
    setToken(null);
    setUser(null);
    navigate('/login');
  };

  return (
    <AuthContext.Provider value={{ user, token, loading, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
