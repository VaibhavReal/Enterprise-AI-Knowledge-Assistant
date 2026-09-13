import React from 'react';
import { Message } from '../types';
import ReactMarkdown from 'react-markdown';
import { User, Bot } from 'lucide-react';
import CitationCard from './CitationCard';

interface Props {
  message: Message;
  isLoading?: boolean;
}

const MessageBubble: React.FC<Props> = ({ message, isLoading }) => {
  const isUser = message.role === 'user';

  return (
    <div className={`flex gap-4 w-full ${isUser ? 'justify-end' : 'justify-start'}`}>
      {!isUser && (
        <div className="w-8 h-8 rounded-full bg-blue-600 flex items-center justify-center flex-shrink-0 mt-1">
          <Bot size={18} className="text-white" />
        </div>
      )}
      
      <div className={`max-w-[80%] ${isUser ? 'order-1' : 'order-2'}`}>
        <div className={`p-4 rounded-2xl ${
          isUser 
            ? 'bg-blue-600 text-white rounded-tr-sm' 
            : 'bg-slate-800 text-slate-200 border border-slate-700 rounded-tl-sm'
        }`}>
          {isLoading ? (
            <div className="flex gap-1 items-center h-6">
              <div className="w-2 h-2 rounded-full bg-slate-400 animate-bounce" style={{ animationDelay: '0ms' }} />
              <div className="w-2 h-2 rounded-full bg-slate-400 animate-bounce" style={{ animationDelay: '150ms' }} />
              <div className="w-2 h-2 rounded-full bg-slate-400 animate-bounce" style={{ animationDelay: '300ms' }} />
            </div>
          ) : (
            <div className={`prose prose-invert max-w-none ${isUser ? 'prose-p:text-white' : ''}`}>
              <ReactMarkdown>{message.content}</ReactMarkdown>
            </div>
          )}
        </div>
        
        {/* Citations */}
        {message.sources && message.sources.length > 0 && (
          <div className="mt-3 space-y-2">
            <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1">Sources</div>
            <div className="grid gap-2">
              {message.sources.map((citation, idx) => (
                <CitationCard key={idx} citation={citation} index={idx + 1} />
              ))}
            </div>
          </div>
        )}
      </div>

      {isUser && (
        <div className="w-8 h-8 rounded-full bg-slate-600 flex items-center justify-center flex-shrink-0 mt-1 order-3">
          <User size={18} className="text-slate-300" />
        </div>
      )}
    </div>
  );
};

export default MessageBubble;
