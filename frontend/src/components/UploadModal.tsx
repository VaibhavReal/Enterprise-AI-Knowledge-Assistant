import React, { useState, useRef } from 'react';
import { X, UploadCloud, File, Loader2, Sparkles, ChevronDown, ChevronUp } from 'lucide-react';
import { uploadDocument } from '../services/api';

interface Props {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
}

const UploadModal: React.FC<Props> = ({ isOpen, onClose, onSuccess }) => {
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState('');
  const [showAdvanced, setShowAdvanced] = useState(false);
  
  const [formData, setFormData] = useState({
    company_name: '',
    ticker: '',
    document_type: '',
    reporting_period: '',
    fiscal_year: ''
  });

  const fileInputRef = useRef<HTMLInputElement>(null);

  if (!isOpen) return null;

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      setFile(e.dataTransfer.files[0]);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file) {
      setError('Please select a financial document to upload');
      return;
    }

    setUploading(true);
    setError('');

    const data = new FormData();
    data.append('file', file);
    if (formData.company_name.trim()) data.append('company_name', formData.company_name.trim());
    if (formData.ticker.trim()) data.append('ticker', formData.ticker.trim());
    if (formData.document_type.trim()) data.append('document_type', formData.document_type.trim());
    if (formData.reporting_period.trim()) data.append('reporting_period', formData.reporting_period.trim());
    if (formData.fiscal_year.trim()) data.append('fiscal_year', formData.fiscal_year.trim());

    try {
      await uploadDocument(data);
      onSuccess();
      onClose();
      // Reset state
      setFile(null);
      setFormData({ company_name: '', ticker: '', document_type: '', reporting_period: '', fiscal_year: '' });
      setShowAdvanced(false);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to process and ingest document');
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4">
      <div className="bg-slate-800 rounded-xl w-full max-w-lg shadow-2xl border border-slate-700 flex flex-col max-h-[90vh]">
        <div className="flex justify-between items-center p-5 border-b border-slate-700">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-blue-500/20 text-blue-400 flex items-center justify-center">
              <UploadCloud size={18} />
            </div>
            <div>
              <h2 className="text-lg font-semibold text-white">Upload Financial Document</h2>
              <p className="text-xs text-slate-400">PDF, DOCX, or TXT (Annual Reports, 10-K, 10-Q, Transcripts)</p>
            </div>
          </div>
          <button onClick={onClose} className="text-slate-400 hover:text-white transition-colors">
            <X size={20} />
          </button>
        </div>

        <div className="p-5 overflow-y-auto space-y-4">
          {error && (
            <div className="p-3 bg-red-500/20 border border-red-500/50 text-red-400 rounded-md text-sm">
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            {/* Dropzone */}
            <div 
              className={`border-2 border-dashed rounded-xl p-8 flex flex-col items-center justify-center text-center cursor-pointer transition-all duration-200 ${
                file 
                  ? 'border-emerald-500 bg-emerald-500/10' 
                  : 'border-slate-600 hover:border-blue-500 bg-slate-900/50 hover:bg-slate-900'
              }`}
              onClick={() => fileInputRef.current?.click()}
              onDragOver={handleDragOver}
              onDrop={handleDrop}
            >
              <input 
                type="file" 
                ref={fileInputRef} 
                className="hidden" 
                accept=".pdf,.docx,.txt"
                onChange={(e) => setFile(e.target.files?.[0] || null)}
              />
              
              {file ? (
                <div className="flex flex-col items-center">
                  <div className="w-12 h-12 rounded-full bg-emerald-500/20 text-emerald-400 flex items-center justify-center mb-2">
                    <File size={24} />
                  </div>
                  <p className="text-base font-semibold text-emerald-400">{file.name}</p>
                  <p className="text-xs text-slate-400 mt-1">{(file.size / 1024 / 1024).toFixed(2)} MB • Ready for AI parsing</p>
                </div>
              ) : (
                <div className="flex flex-col items-center">
                  <div className="w-12 h-12 rounded-full bg-blue-500/10 text-blue-400 flex items-center justify-center mb-2">
                    <UploadCloud size={24} />
                  </div>
                  <p className="text-base font-medium text-slate-200 mb-1">Click to browse or drag financial report here</p>
                  <p className="text-xs text-slate-400">Supports SEC Filings (10-K, 10-Q), Annual Reports, Earnings Transcripts</p>
                </div>
              )}
            </div>

            {/* AI Auto-Extraction Feature Callout */}
            <div className="p-3.5 bg-blue-500/10 border border-blue-500/20 rounded-lg flex items-start gap-3">
              <Sparkles size={18} className="text-blue-400 flex-shrink-0 mt-0.5" />
              <div className="text-xs text-slate-300 leading-relaxed">
                <span className="font-semibold text-blue-300">Automatic Document Intelligence:</span> Company name, ticker, filing type (10-K/10-Q), reporting period, and fiscal year will be automatically analyzed and extracted directly from your document.
              </div>
            </div>

            {/* Optional Advanced Accordion */}
            <div className="border border-slate-700/60 rounded-lg overflow-hidden bg-slate-900/30">
              <button
                type="button"
                onClick={() => setShowAdvanced(!showAdvanced)}
                className="w-full px-4 py-2.5 flex justify-between items-center text-xs font-medium text-slate-400 hover:text-slate-200 transition-colors"
              >
                <span>Manual Metadata Overrides (Optional)</span>
                {showAdvanced ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
              </button>

              {showAdvanced && (
                <div className="p-4 border-t border-slate-700/60 space-y-3 bg-slate-900/60">
                  <div className="grid grid-cols-2 gap-3">
                    <div className="space-y-1">
                      <label className="text-xs font-medium text-slate-400">Company Name</label>
                      <input 
                        type="text" 
                        value={formData.company_name} 
                        onChange={(e) => setFormData({...formData, company_name: e.target.value})}
                        className="w-full bg-slate-900 border border-slate-700 rounded-md px-3 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-blue-500"
                        placeholder="Auto-detected if blank"
                      />
                    </div>
                    <div className="space-y-1">
                      <label className="text-xs font-medium text-slate-400">Ticker</label>
                      <input 
                        type="text" 
                        value={formData.ticker} 
                        onChange={(e) => setFormData({...formData, ticker: e.target.value})}
                        className="w-full bg-slate-900 border border-slate-700 rounded-md px-3 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-blue-500 uppercase"
                        placeholder="Auto-detected (e.g. AAPL)"
                      />
                    </div>
                  </div>

                  <div className="grid grid-cols-3 gap-3">
                    <div className="space-y-1">
                      <label className="text-xs font-medium text-slate-400">Document Type</label>
                      <select 
                        value={formData.document_type} 
                        onChange={(e) => setFormData({...formData, document_type: e.target.value})}
                        className="w-full bg-slate-900 border border-slate-700 rounded-md px-2 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-blue-500"
                      >
                        <option value="">Auto-Detect</option>
                        <option value="10-K (Annual Report)">10-K (Annual Report)</option>
                        <option value="10-Q (Quarterly Report)">10-Q (Quarterly Report)</option>
                        <option value="Earnings Call Transcript">Earnings Call Transcript</option>
                        <option value="Investor Presentation">Investor Presentation</option>
                        <option value="Financial Statements">Financial Statements</option>
                      </select>
                    </div>

                    <div className="space-y-1">
                      <label className="text-xs font-medium text-slate-400">Period</label>
                      <input 
                        type="text" 
                        value={formData.reporting_period} 
                        onChange={(e) => setFormData({...formData, reporting_period: e.target.value})}
                        className="w-full bg-slate-900 border border-slate-700 rounded-md px-3 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-blue-500"
                        placeholder="e.g. Q3 or Full Year"
                      />
                    </div>

                    <div className="space-y-1">
                      <label className="text-xs font-medium text-slate-400">Fiscal Year</label>
                      <input 
                        type="text" 
                        value={formData.fiscal_year} 
                        onChange={(e) => setFormData({...formData, fiscal_year: e.target.value})}
                        className="w-full bg-slate-900 border border-slate-700 rounded-md px-3 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-blue-500"
                        placeholder="e.g. 2024"
                      />
                    </div>
                  </div>
                </div>
              )}
            </div>

            <div className="pt-3 border-t border-slate-700 flex justify-end gap-3">
              <button 
                type="button" 
                onClick={onClose}
                className="px-4 py-2 text-sm font-medium text-slate-300 hover:text-white"
                disabled={uploading}
              >
                Cancel
              </button>
              <button 
                type="submit" 
                disabled={!file || uploading}
                className="px-5 py-2.5 bg-blue-600 hover:bg-blue-700 text-white text-sm font-semibold rounded-lg transition-all shadow-md hover:shadow-blue-500/20 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
              >
                {uploading ? (
                  <>
                    <Loader2 size={16} className="animate-spin" />
                    <span>Parsing & Ingesting...</span>
                  </>
                ) : (
                  <>
                    <Sparkles size={16} />
                    <span>Process & Ingest Document</span>
                  </>
                )}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
};

export default UploadModal;
