import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { getDocument, deleteDocument, createChat } from '../services/api';
import { Document } from '../types';
import { ArrowLeft, Trash2, MessageSquare, Loader2, FileText, CheckCircle2, XCircle } from 'lucide-react';

const DocumentDetailPage = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const [doc, setDoc] = useState<Document | null>(null);
  const [loading, setLoading] = useState(true);
  const [startingChat, setStartingChat] = useState(false);

  useEffect(() => {
    if (!id) return;
    const fetchDoc = async () => {
      try {
        const res = await getDocument(Number(id));
        setDoc(res.data);
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    };
    fetchDoc();
  }, [id]);

  const handleDelete = async () => {
    if (!doc || !window.confirm('Are you sure you want to delete this document?')) return;
    try {
      await deleteDocument(doc.id);
      navigate('/documents');
    } catch (err) {
      alert('Failed to delete document');
    }
  };

  const handleStartChat = async () => {
    if (!doc) return;
    setStartingChat(true);
    try {
      const res = await createChat({ 
        title: `Analysis: ${doc.company_name || doc.original_filename}`,
        document_ids: [doc.id] 
      });
      navigate(`/chats/${res.data.id}`);
    } catch (err) {
      console.error(err);
      alert('Failed to start chat');
    } finally {
      setStartingChat(false);
    }
  };

  if (loading) return <div className="p-8 text-center text-slate-400">Loading document details...</div>;
  if (!doc) return <div className="p-8 text-center text-red-400">Document not found</div>;

  const getStatusDisplay = () => {
    switch (doc.status) {
      case 'processing': return <div className="flex items-center gap-2 text-yellow-500 bg-yellow-500/10 px-3 py-1.5 rounded-full text-sm font-medium"><Loader2 className="animate-spin" size={16} /> Processing</div>;
      case 'ready': return <div className="flex items-center gap-2 text-emerald-500 bg-emerald-500/10 px-3 py-1.5 rounded-full text-sm font-medium"><CheckCircle2 size={16} /> Ready</div>;
      case 'failed': return <div className="flex items-center gap-2 text-red-500 bg-red-500/10 px-3 py-1.5 rounded-full text-sm font-medium"><XCircle size={16} /> Failed</div>;
    }
  };

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <button 
        onClick={() => navigate('/documents')}
        className="flex items-center gap-2 text-slate-400 hover:text-white transition-colors"
      >
        <ArrowLeft size={16} /> Back to Documents
      </button>

      <div className="bg-slate-800 border border-slate-700 rounded-xl overflow-hidden">
        <div className="p-6 border-b border-slate-700 flex justify-between items-start">
          <div className="flex items-start gap-4">
            <div className="p-3 bg-blue-500/10 text-blue-400 rounded-xl">
              <FileText size={32} />
            </div>
            <div>
              <h1 className="text-xl font-bold text-white mb-2">{doc.original_filename}</h1>
              {getStatusDisplay()}
            </div>
          </div>
          
          <div className="flex gap-3">
            <button 
              onClick={handleDelete}
              className="p-2 text-slate-400 hover:text-red-400 hover:bg-red-400/10 rounded-lg transition-colors"
              title="Delete Document"
            >
              <Trash2 size={20} />
            </button>
            <button 
              onClick={handleStartChat}
              disabled={doc.status !== 'ready' || startingChat}
              className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg font-medium flex items-center gap-2 transition-colors disabled:opacity-50"
            >
              {startingChat ? <Loader2 className="animate-spin" size={18} /> : <MessageSquare size={18} />}
              Start Research Chat
            </button>
          </div>
        </div>

        <div className="p-6">
          <h3 className="text-sm font-semibold text-slate-400 uppercase tracking-wider mb-4">Document Metadata</h3>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="bg-slate-900/50 p-4 rounded-lg border border-slate-700/50">
              <div className="text-xs text-slate-500 mb-1">Company Name</div>
              <div className="font-medium">{doc.company_name || '—'}</div>
            </div>
            
            <div className="bg-slate-900/50 p-4 rounded-lg border border-slate-700/50">
              <div className="text-xs text-slate-500 mb-1">Ticker</div>
              <div className="font-medium uppercase">{doc.ticker || '—'}</div>
            </div>

            <div className="bg-slate-900/50 p-4 rounded-lg border border-slate-700/50">
              <div className="text-xs text-slate-500 mb-1">Document Type</div>
              <div className="font-medium">{doc.document_type || '—'}</div>
            </div>

            <div className="bg-slate-900/50 p-4 rounded-lg border border-slate-700/50">
              <div className="text-xs text-slate-500 mb-1">Reporting Period</div>
              <div className="font-medium">{doc.reporting_period ? `${doc.reporting_period} ${doc.fiscal_year || ''}` : '—'}</div>
            </div>

            <div className="bg-slate-900/50 p-4 rounded-lg border border-slate-700/50">
              <div className="text-xs text-slate-500 mb-1">File Size</div>
              <div className="font-medium">{(doc.file_size_bytes / 1024 / 1024).toFixed(2)} MB</div>
            </div>

            <div className="bg-slate-900/50 p-4 rounded-lg border border-slate-700/50">
              <div className="text-xs text-slate-500 mb-1">Processing Chunks</div>
              <div className="font-medium">{doc.num_chunks}</div>
            </div>
            
            <div className="bg-slate-900/50 p-4 rounded-lg border border-slate-700/50 md:col-span-2">
              <div className="text-xs text-slate-500 mb-1">Upload Date</div>
              <div className="font-medium">{new Date(doc.created_at).toLocaleString()}</div>
            </div>
          </div>
          
          {doc.error_message && (
            <div className="mt-4 p-4 bg-red-500/10 border border-red-500/30 rounded-lg">
              <h4 className="text-sm font-semibold text-red-400 mb-1">Processing Error</h4>
              <p className="text-sm text-red-300/80">{doc.error_message}</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default DocumentDetailPage;
