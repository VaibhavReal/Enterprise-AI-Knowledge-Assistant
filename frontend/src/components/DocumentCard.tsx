import React from 'react';
import { Document } from '../types';
import { FileText, Loader2, CheckCircle2, XCircle, Trash2 } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

interface Props {
  document: Document;
  onDelete?: (id: number) => void;
}

const DocumentCard: React.FC<Props> = ({ document: doc, onDelete }) => {
  const navigate = useNavigate();

  const getStatusIcon = () => {
    switch (doc.status) {
      case 'processing': return <Loader2 className="animate-spin text-yellow-500" size={16} />;
      case 'ready': return <CheckCircle2 className="text-emerald-500" size={16} />;
      case 'failed': return <XCircle className="text-red-500" size={16} />;
    }
  };

  const getTypeColor = (type: string | null) => {
    if (!type) return 'bg-slate-700 text-slate-300';
    if (type.toLowerCase().includes('annual') || type.includes('10-K')) return 'bg-blue-500/20 text-blue-400 border-blue-500/30';
    if (type.toLowerCase().includes('quarterly') || type.includes('10-Q')) return 'bg-purple-500/20 text-purple-400 border-purple-500/30';
    if (type.toLowerCase().includes('earnings')) return 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30';
    return 'bg-slate-700 text-slate-300';
  };

  return (
    <div className="bg-slate-800 border border-slate-700 rounded-lg p-4 hover:border-slate-500 transition-colors group cursor-pointer" onClick={() => navigate(`/documents/${doc.id}`)}>
      <div className="flex justify-between items-start mb-3">
        <div className="flex items-center gap-2 overflow-hidden">
          <FileText className="text-slate-400 flex-shrink-0" size={20} />
          <h3 className="font-medium text-slate-200 truncate" title={doc.original_filename}>{doc.original_filename}</h3>
        </div>
        {onDelete && (
          <button 
            onClick={(e) => { e.stopPropagation(); onDelete(doc.id); }} 
            className="text-slate-500 hover:text-red-400 opacity-0 group-hover:opacity-100 transition-opacity"
            title="Delete Document"
          >
            <Trash2 size={16} />
          </button>
        )}
      </div>

      <div className="space-y-2 mb-4">
        {doc.company_name && (
          <div className="flex items-center gap-2 text-sm">
            <span className="font-semibold text-slate-300">{doc.company_name}</span>
            {doc.ticker && <span className="px-1.5 py-0.5 bg-slate-700 rounded text-xs font-mono text-slate-400">{doc.ticker}</span>}
          </div>
        )}
        
        <div className="flex flex-wrap gap-2">
          {doc.document_type && (
            <span className={`text-xs px-2 py-1 rounded border ${getTypeColor(doc.document_type)}`}>
              {doc.document_type}
            </span>
          )}
          {doc.reporting_period && (
            <span className="text-xs px-2 py-1 rounded bg-slate-700/50 text-slate-400 border border-slate-600/50">
              {doc.reporting_period} {doc.fiscal_year}
            </span>
          )}
        </div>
      </div>

      <div className="flex justify-between items-center text-xs text-slate-500 pt-3 border-t border-slate-700/50">
        <div className="flex items-center gap-1.5">
          {getStatusIcon()}
          <span className="capitalize">{doc.status}</span>
        </div>
        <div className="flex gap-3">
          <span>{doc.num_chunks} chunks</span>
          <span>{new Date(doc.created_at).toLocaleDateString()}</span>
        </div>
      </div>
    </div>
  );
};

export default DocumentCard;
