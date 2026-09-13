import { ReactNode } from 'react';
import { NavLink } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import { LayoutDashboard, FileText, MessageSquare, LogOut, Briefcase } from 'lucide-react';

const Layout = ({ children }: { children: ReactNode }) => {
  const { user, logout } = useAuth();

  return (
    <div className="flex h-screen bg-slate-900 text-slate-100 overflow-hidden">
      {/* Sidebar */}
      <aside className="w-64 bg-slate-800 border-r border-slate-700 flex flex-col">
        <div className="p-4 flex items-center gap-3 border-b border-slate-700">
          <Briefcase className="text-emerald-500" />
          <h1 className="font-bold text-lg tracking-tight">FinResearch AI</h1>
        </div>
        
        <nav className="flex-1 p-4 space-y-2">
          <NavLink to="/dashboard" className={({isActive}) => `flex items-center gap-3 px-3 py-2 rounded-md transition-colors ${isActive ? 'bg-blue-600 text-white' : 'hover:bg-slate-700 text-slate-300'}`}>
            <LayoutDashboard size={18} /> Dashboard
          </NavLink>
          <NavLink to="/documents" className={({isActive}) => `flex items-center gap-3 px-3 py-2 rounded-md transition-colors ${isActive ? 'bg-blue-600 text-white' : 'hover:bg-slate-700 text-slate-300'}`}>
            <FileText size={18} /> Documents
          </NavLink>
          <NavLink to="/chats" className={({isActive}) => `flex items-center gap-3 px-3 py-2 rounded-md transition-colors ${isActive ? 'bg-blue-600 text-white' : 'hover:bg-slate-700 text-slate-300'}`}>
            <MessageSquare size={18} /> Research Chats
          </NavLink>
        </nav>

        <div className="p-4 border-t border-slate-700 text-xs text-slate-500">
          <p>This system is for financial research and educational purposes only and does not constitute investment advice.</p>
        </div>
      </aside>

      {/* Main Content */}
      <div className="flex-1 flex flex-col min-w-0">
        <header className="h-16 border-b border-slate-700 bg-slate-800 flex items-center justify-between px-6">
          <div className="flex items-center">
          </div>
          <div className="flex items-center gap-4">
            <span className="text-sm font-medium text-slate-300">{user?.full_name}</span>
            <button onClick={logout} className="p-2 text-slate-400 hover:text-white rounded-full hover:bg-slate-700 transition-colors">
              <LogOut size={18} />
            </button>
          </div>
        </header>
        
        <main className="flex-1 overflow-auto bg-slate-900 p-6">
          {children}
        </main>
      </div>
    </div>
  );
};

export default Layout;
