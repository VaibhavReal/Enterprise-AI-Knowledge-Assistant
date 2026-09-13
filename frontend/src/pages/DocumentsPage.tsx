import { useEffect, useState } from 'react';
import { listDocuments, deleteDocument } from '../services/api';
import { Document } from '../types';
import DocumentCard from '../components/DocumentCard';
import UploadModal from '../components/UploadModal';
import { Upload, Search, Filter, FileText } from 'lucide-react';

const DocumentsPage = () => {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [loading, setLoading] = useState(true);
  const [isUploadModalOpen, setIsUploadModalOpen] = useState(false);
  
  // Filters
  const [searchQuery, setSearchQuery] = useState('');
  const [typeFilter, setTypeFilter] = useState('');

  const fetchDocuments = async () => {
    setLoading(true);
    try {
      const filters: any = {};
      if (searchQuery) filters.company_name = searchQuery;
      if (typeFilter) filters.document_type = typeFilter;
      
      const res = await listDocuments(filters);
      setDocuments(res.data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDocuments();
  }, [searchQuery, typeFilter]);

  const handleDelete = async (id: number) => {
    if (!window.confirm('Are you sure you want to delete this document?')) return;
    try {
      await deleteDocument(id);
      fetchDocuments();
    } catch (err) {
      console.error('Failed to delete', err);
      alert('Failed to delete document');
    }
  };

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white">Document Library</h1>
          <p className="text-slate-400 text-sm mt-1">Manage and view your uploaded financial documents.</p>
        </div>
        <button 
          onClick={() => setIsUploadModalOpen(true)}
          className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-md font-medium flex items-center gap-2 transition-colors"
        >
          <Upload size={18} /> Upload Document
        </button>
      </div>

      {/* Filters */}
      <div className="flex flex-col sm:flex-row gap-4 bg-slate-800 p-4 rounded-xl border border-slate-700">
        <div className="flex-1 relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" size={18} />
          <input 
            type="text" 
            placeholder="Search by company name..." 
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full bg-slate-900 border border-slate-600 rounded-md pl-10 pr-4 py-2 text-sm focus:outline-none focus:border-blue-500"
          />
        </div>
        <div className="relative min-w-[200px]">
          <Filter className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" size={18} />
          <select
            value={typeFilter}
            onChange={(e) => setTypeFilter(e.target.value)}
            className="w-full bg-slate-900 border border-slate-600 rounded-md pl-10 pr-4 py-2 text-sm focus:outline-none focus:border-blue-500 appearance-none"
          >
            <option value="">All Document Types</option>
            <option value="10-K">10-K (Annual Report)</option>
            <option value="10-Q">10-Q (Quarterly Report)</option>
            <option value="Earnings Call Transcript">Earnings Call Transcript</option>
            <option value="Investor Presentation">Investor Presentation</option>
          </select>
        </div>
      </div>

      {loading ? (
        <div className="text-center py-12 text-slate-400">Loading documents...</div>
      ) : documents.length === 0 ? (
        <div className="bg-slate-800/50 border border-slate-700 rounded-xl p-12 text-center">
          <FileText size={48} className="mx-auto text-slate-600 mb-4" />
          <h3 className="text-lg font-medium text-white mb-2">No documents found</h3>
          <p className="text-slate-400 mb-6">Upload documents to start your financial analysis.</p>
          <button 
            onClick={() => setIsUploadModalOpen(true)}
            className="text-blue-500 font-medium hover:underline"
          >
            Upload your first document
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {documents.map(doc => (
            <DocumentCard key={doc.id} document={doc} onDelete={handleDelete} />
          ))}
        </div>
      )}

      <UploadModal 
        isOpen={isUploadModalOpen} 
        onClose={() => setIsUploadModalOpen(false)} 
        onSuccess={fetchDocuments} 
      />
    </div>
  );
};

export default DocumentsPage;
