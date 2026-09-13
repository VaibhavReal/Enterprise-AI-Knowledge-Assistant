import React, { useState } from 'react';
import { Citation } from '../types';
import { FileText, ChevronDown, ChevronUp } from 'lucide-react';

interface Props {
  citation: Citation;
  index: number;
}

const CitationCard: React.FC<Props> = ({ citation, index }) => {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="bg-slate-800/50 border border-slate-700/50 rounded-md p-3 text-sm">
      <div className="flex justify-between items-start mb-2">
        <div className="flex items-center gap-2 text-blue-400 font-medium">
          <span className="bg-blue-500/20 w-5 h-5 flex items-center justify-center rounded-full text-xs">{index}</span>
          <FileText size={14} />
          <span className="truncate max-w-[200px]" title={citation.document_name}>{citation.document_name}</span>
          {(citation.page_number || citation.section_title) && (
            <span className="text-slate-500 text-xs font-normal">
              ({citation.page_number ? `p. ${citation.page_number}` : ''}{citation.page_number && citation.section_title ? ', ' : ''}{citation.section_title})
            </span>
          )}
        </div>
        
        <div className="flex items-center gap-2" title={`Relevance: ${Math.round(citation.relevance_score * 100)}%`}>
          <div className="w-16 h-1.5 bg-slate-700 rounded-full overflow-hidden">
            <div 
              className="h-full bg-emerald-500" 
              style={{ width: `${Math.min(100, Math.max(0, citation.relevance_score * 100))}%` }}
            />
          </div>
        </div>
      </div>

      <div className="text-slate-300 relative">
        <div className={expanded ? '' : 'line-clamp-2'}>
          "{citation.content_snippet}"
        </div>
        
        {citation.content_snippet.length > 150 && (
          <button 
            onClick={() => setExpanded(!expanded)} 
            className="flex items-center gap-1 text-xs text-blue-400 hover:text-blue-300 mt-1"
          >
            {expanded ? <><ChevronUp size={12}/> Show less</> : <><ChevronDown size={12}/> Show more</>}
          </button>
        )}
      </div>
    </div>
  );
};

export default CitationCard;
