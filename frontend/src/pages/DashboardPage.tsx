import { useEffect, useState } from 'react';
import { useAuth } from '../hooks/useAuth';
import { listDocuments, listChats, createChat } from '../services/api';
import { Document, Chat } from '../types';
import DocumentCard from '../components/DocumentCard';
import { PlusSquare, Upload, MessageSquare, FileText } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import UploadModal from '../components/UploadModal';

const DashboardPage = () => {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [documents, setDocuments] = useState<Document[]>([]);
  const [chats, setChats] = useState<Chat[]>([]);
  const [isUploadModalOpen, setIsUploadModalOpen] = useState(false);
  const [creatingChat, setCreatingChat] = useState(false);

  const fetchData = async () => {
    try {
      const [docsRes, chatsRes] = await Promise.all([
        listDocuments(),
        listChats()
      ]);
      setDocuments(docsRes.data);
      setChats(chatsRes.data);
    } catch (err) {
      console.error("Failed to fetch dashboard data", err);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleNewChat = async () => {
    setCreatingChat(true);
    try {
      const res = await createChat({ title: "New Research Session" });
      navigate(`/chats/${res.data.id}`);
    } catch (err) {
      console.error(err);
    } finally {
      setCreatingChat(false);
    }
  };

  const readyDocs = documents.filter(d => d.status === 'ready').length;

  return (
    <div className="max-w-6xl mx-auto space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-white mb-2">Welcome back, {user?.full_name}</h1>
        <p className="text-slate-400">Here's an overview of your financial research workspace.</p>
      </div>

      {/* Stats Row */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-slate-800 border border-slate-700 p-5 rounded-xl">
          <div className="flex items-center gap-3 mb-2">
            <div className="p-2 bg-blue-500/20 text-blue-400 rounded-lg"><FileText size={20} /></div>
            <h3 className="font-semibold text-slate-300">Total Documents</h3>
          </div>
          <p className="text-3xl font-bold">{documents.length}</p>
        </div>
        
        <div className="bg-slate-800 border border-slate-700 p-5 rounded-xl">
          <div className="flex items-center gap-3 mb-2">
            <div className="p-2 bg-emerald-500/20 text-emerald-400 rounded-lg"><FileText size={20} /></div>
            <h3 className="font-semibold text-slate-300">Ready for Analysis</h3>
          </div>
          <p className="text-3xl font-bold">{readyDocs}</p>
        </div>

        <div className="bg-slate-800 border border-slate-700 p-5 rounded-xl">
          <div className="flex items-center gap-3 mb-2">
            <div className="p-2 bg-purple-500/20 text-purple-400 rounded-lg"><MessageSquare size={20} /></div>
            <h3 className="font-semibold text-slate-300">Research Chats</h3>
          </div>
          <p className="text-3xl font-bold">{chats.length}</p>
        </div>
      </div>

      {/* Actions */}
      <div className="flex gap-4">
        <button 
          onClick={handleNewChat}
          disabled={creatingChat}
          className="flex-1 bg-blue-600 hover:bg-blue-700 text-white p-4 rounded-xl font-medium flex items-center justify-center gap-2 transition-colors disabled:opacity-50"
        >
          <PlusSquare size={20} /> Start New Research Session
        </button>
        <button 
          onClick={() => setIsUploadModalOpen(true)}
          className="flex-1 bg-slate-800 hover:bg-slate-700 border border-slate-600 text-white p-4 rounded-xl font-medium flex items-center justify-center gap-2 transition-colors"
        >
          <Upload size={20} /> Upload Document
        </button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Recent Documents */}
        <div>
          <div className="flex justify-between items-end mb-4">
            <h2 className="text-lg font-semibold text-white">Recent Documents</h2>
            <button onClick={() => navigate('/documents')} className="text-sm text-blue-400 hover:text-blue-300">View all</button>
          </div>
          {documents.length === 0 ? (
            <div className="bg-slate-800 border border-slate-700 rounded-xl p-8 text-center">
              <p className="text-slate-400 mb-4">No documents uploaded yet.</p>
              <button onClick={() => setIsUploadModalOpen(true)} className="text-blue-500 font-medium hover:underline">Upload your first document</button>
            </div>
          ) : (
            <div className="space-y-3">
              {documents.slice(0, 5).map(doc => (
                <DocumentCard key={doc.id} document={doc} />
              ))}
            </div>
          )}
        </div>

        {/* Recent Chats */}
        <div>
          <div className="flex justify-between items-end mb-4">
            <h2 className="text-lg font-semibold text-white">Recent Chats</h2>
            <button onClick={() => navigate('/chats')} className="text-sm text-blue-400 hover:text-blue-300">View all</button>
          </div>
          {chats.length === 0 ? (
            <div className="bg-slate-800 border border-slate-700 rounded-xl p-8 text-center">
              <p className="text-slate-400">No chats started yet.</p>
            </div>
          ) : (
            <div className="space-y-3">
              {chats.slice(0, 5).map(chat => (
                <div 
                  key={chat.id} 
                  onClick={() => navigate(`/chats/${chat.id}`)}
                  className="bg-slate-800 border border-slate-700 p-4 rounded-xl hover:border-slate-500 cursor-pointer transition-colors"
                >
                  <div className="flex items-center gap-3">
                    <MessageSquare size={18} className="text-slate-400" />
                    <span className="font-medium text-slate-200">{chat.title || 'Untitled Chat'}</span>
                  </div>
                  <div className="text-xs text-slate-500 mt-2 pl-7">
                    {new Date(chat.updated_at).toLocaleString()}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      <UploadModal 
        isOpen={isUploadModalOpen} 
        onClose={() => setIsUploadModalOpen(false)} 
        onSuccess={fetchData} 
      />
    </div>
  );
};

export default DashboardPage;
