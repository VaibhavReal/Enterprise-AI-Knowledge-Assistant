import { useEffect, useState } from 'react';
import { listChats, createChat } from '../services/api';
import { Chat } from '../types';
import { MessageSquare, PlusSquare, ChevronRight } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

const ChatHistoryPage = () => {
  const [chats, setChats] = useState<Chat[]>([]);
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const navigate = useNavigate();

  useEffect(() => {
    const fetchChats = async () => {
      try {
        const res = await listChats();
        setChats(res.data);
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    };
    fetchChats();
  }, []);

  const handleNewChat = async () => {
    setCreating(true);
    try {
      const res = await createChat({ title: "New Research Session" });
      navigate(`/chats/${res.data.id}`);
    } catch (err) {
      console.error(err);
      alert("Failed to create chat");
    } finally {
      setCreating(false);
    }
  };

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-white">Research Chats</h1>
          <p className="text-slate-400 text-sm mt-1">Review your past financial research conversations.</p>
        </div>
        <button 
          onClick={handleNewChat}
          disabled={creating}
          className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-md font-medium flex items-center gap-2 transition-colors disabled:opacity-50"
        >
          <PlusSquare size={18} /> New Chat
        </button>
      </div>

      {loading ? (
        <div className="text-center py-12 text-slate-400">Loading chats...</div>
      ) : chats.length === 0 ? (
        <div className="bg-slate-800/50 border border-slate-700 rounded-xl p-12 text-center">
          <MessageSquare size={48} className="mx-auto text-slate-600 mb-4" />
          <h3 className="text-lg font-medium text-white mb-2">No research chats yet</h3>
          <p className="text-slate-400 mb-6">Start a new chat to begin analyzing your financial documents.</p>
          <button 
            onClick={handleNewChat}
            className="text-blue-500 font-medium hover:underline"
          >
            Start your first session
          </button>
        </div>
      ) : (
        <div className="space-y-3">
          {chats.map(chat => (
            <div 
              key={chat.id} 
              onClick={() => navigate(`/chats/${chat.id}`)}
              className="bg-slate-800 border border-slate-700 p-5 rounded-xl hover:border-slate-500 cursor-pointer transition-all flex items-center justify-between group"
            >
              <div className="flex items-start gap-4">
                <div className="mt-1 bg-slate-700/50 p-2 rounded-lg text-slate-400 group-hover:text-blue-400 transition-colors">
                  <MessageSquare size={20} />
                </div>
                <div>
                  <h3 className="font-semibold text-slate-200 text-lg group-hover:text-blue-400 transition-colors">
                    {chat.title || 'Untitled Research Session'}
                  </h3>
                  <div className="flex items-center gap-4 mt-1 text-sm text-slate-500">
                    <span>{new Date(chat.created_at).toLocaleDateString()} at {new Date(chat.created_at).toLocaleTimeString()}</span>
                    {chat.document_ids && chat.document_ids.length > 0 && (
                      <span className="bg-slate-700 px-2 py-0.5 rounded text-xs">
                        {chat.document_ids.length} document{chat.document_ids.length > 1 ? 's' : ''} attached
                      </span>
                    )}
                  </div>
                </div>
              </div>
              <ChevronRight className="text-slate-600 group-hover:text-blue-400 transition-colors" />
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default ChatHistoryPage;
