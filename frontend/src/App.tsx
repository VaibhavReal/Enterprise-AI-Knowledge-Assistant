import { ReactNode } from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import LoginPage from './pages/LoginPage';
import RegisterPage from './pages/RegisterPage';
import DashboardPage from './pages/DashboardPage';
import DocumentsPage from './pages/DocumentsPage';
import DocumentDetailPage from './pages/DocumentDetailPage';
import ChatHistoryPage from './pages/ChatHistoryPage';
import ChatPage from './pages/ChatPage';
import Layout from './components/Layout';
import { useAuth } from './hooks/useAuth';

const ProtectedRoute = ({ children }: { children: ReactNode }) => {
  const { token, loading } = useAuth();
  
  if (loading) return <div className="min-h-screen flex items-center justify-center bg-slate-900 text-slate-100">Loading...</div>;
  if (!token) return <Navigate to="/login" replace />;
  
  return <Layout>{children}</Layout>;
};

function App() {
  return (
    <Routes>
      <Route path="/" element={<Navigate to="/dashboard" replace />} />
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />
      
      <Route path="/dashboard" element={<ProtectedRoute><DashboardPage /></ProtectedRoute>} />
      <Route path="/documents" element={<ProtectedRoute><DocumentsPage /></ProtectedRoute>} />
      <Route path="/documents/:id" element={<ProtectedRoute><DocumentDetailPage /></ProtectedRoute>} />
      <Route path="/chats" element={<ProtectedRoute><ChatHistoryPage /></ProtectedRoute>} />
      <Route path="/chats/:id" element={<ProtectedRoute><ChatPage /></ProtectedRoute>} />
    </Routes>
  );
}

export default App;
