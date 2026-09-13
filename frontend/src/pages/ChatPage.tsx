import React, { useState, useEffect, useRef } from 'react';
import { useParams } from 'react-router-dom';
import { getChatMessages, sendMessageStream, listDocuments } from '../services/api';
import { Message, Document, StreamEvent } from '../types';
import MessageBubble from '../components/MessageBubble';
import { Send, Loader2, FileText, MessageSquare } from 'lucide-react';

const ChatPage = () => {
  const { id } = useParams();
  const chatId = Number(id);
  
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(true);
  const [isStreaming, setIsStreaming] = useState(false);
  
  // Document context
  const [allDocs, setAllDocs] = useState<Document[]>([]);
  const [selectedDocIds, setSelectedDocIds] = useState<number[]>([]);
  const [showDocsPanel, setShowDocsPanel] = useState(false);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const abortControllerRef = useRef<AbortController | null>(null);

  useEffect(() => {
    const fetchInitialData = async () => {
      try {
        const [msgsRes, docsRes] = await Promise.all([
          getChatMessages(chatId),
          listDocuments()
        ]);
        // msgsRes.data and docsRes.data are both arrays
        const msgsData = Array.isArray(msgsRes.data) ? msgsRes.data : [];
        const docsData = Array.isArray(docsRes.data) ? docsRes.data : [];
        setMessages(msgsData);
        setAllDocs(docsData.filter((d: Document) => d.status === 'ready'));
      } catch (err) {
        console.error('Failed to load chat data:', err);
      } finally {
        setLoading(false);
      }
    };
    if (chatId) fetchInitialData();
  }, [chatId]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSend = async (e?: React.FormEvent) => {
    e?.preventDefault();
    if (!input.trim() || isStreaming) return;

    const userContent = input.trim();
    setInput('');
    
    // Add user message to UI immediately
    const tempUserMsg: Message = {
      id: Date.now(),
      chat_id: chatId,
      role: 'user',
      content: userContent,
      sources: [],
      created_at: new Date().toISOString()
    };
    
    // Add empty assistant placeholder for streaming
    const tempAsstMsg: Message = {
      id: Date.now() + 1,
      chat_id: chatId,
      role: 'assistant',
      content: '',
      sources: [],
      created_at: new Date().toISOString()
    };

    setMessages(prev => [...prev, tempUserMsg, tempAsstMsg]);
    setIsStreaming(true);

    // Create abort controller so we can cancel if component unmounts
    const abortController = new AbortController();
    abortControllerRef.current = abortController;

    try {
      const docsToUse = selectedDocIds.length > 0 ? selectedDocIds : undefined;
      const response = await sendMessageStream(chatId, userContent, docsToUse);
      
      if (!response.body) throw new Error('No response body from server');
      
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let assistantContent = '';
      let buffer = '';
      let finalCitations: any[] = [];

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        
        // Append decoded bytes to buffer — handles chunk boundaries correctly
        buffer += decoder.decode(value, { stream: true });
        
        // Split on double-newline SSE event separator
        const parts = buffer.split('\n\n');
        // The last element may be an incomplete event — keep it in the buffer
        buffer = parts.pop() || '';
        
        for (const part of parts) {
          const trimmed = part.trim();
          if (!trimmed) continue;
          
          // Handle SSE "data: " prefix
          const dataLine = trimmed.startsWith('data: ') ? trimmed.slice(6).trim() : trimmed;
          if (!dataLine || dataLine === '[DONE]') continue;
          
          try {
            const event: StreamEvent = JSON.parse(dataLine);
            
            if (event.error) {
              assistantContent = `⚠️ ${event.error}`;
              setMessages(prev => {
                const msgs = [...prev];
                msgs[msgs.length - 1] = { ...msgs[msgs.length - 1], content: assistantContent };
                return msgs;
              });
              break;
            }
            
            if (event.token) {
              assistantContent += event.token;
              setMessages(prev => {
                const msgs = [...prev];
                msgs[msgs.length - 1] = { ...msgs[msgs.length - 1], content: assistantContent };
                return msgs;
              });
            }
            
            if (event.done && event.citations) {
              finalCitations = event.citations;
              setMessages(prev => {
                const msgs = [...prev];
                msgs[msgs.length - 1] = { ...msgs[msgs.length - 1], sources: event.citations || [] };
                return msgs;
              });
            }
          } catch (parseErr) {
            // Silently skip malformed SSE events
          }
        }
      }
      
      // After stream completes, refresh messages from DB to get persisted IDs
      // Only do this if the stream actually produced content
      if (assistantContent.trim()) {
        try {
          const refreshed = await getChatMessages(chatId);
          const refreshedData = Array.isArray(refreshed.data) ? refreshed.data : [];
          if (refreshedData.length > 0) {
            setMessages(refreshedData);
          }
        } catch (refreshErr) {
          // Non-critical: keep the optimistically-rendered messages
          console.warn('Could not refresh messages from DB:', refreshErr);
        }
      }

    } catch (err: any) {
      if (err?.name === 'AbortError') return; // Component unmounted, ignore
      console.error('Error sending message:', err);
      setMessages(prev => {
        const msgs = [...prev];
        const errorText = err?.message || 'Sorry, an error occurred while processing your request.';
        msgs[msgs.length - 1] = { ...msgs[msgs.length - 1], content: `⚠️ ${errorText}` };
        return msgs;
      });
    } finally {
      setIsStreaming(false);
      abortControllerRef.current = null;
    }
  };

  // Cleanup abort controller on unmount
  useEffect(() => {
    return () => {
      abortControllerRef.current?.abort();
    };
  }, []);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const toggleDocSelection = (id: number) => {
    setSelectedDocIds(prev => 
      prev.includes(id) ? prev.filter(docId => docId !== id) : [...prev, id]
    );
  };

  if (loading) return <div className="h-full flex items-center justify-center"><Loader2 className="animate-spin text-blue-500" size={32} /></div>;

  return (
    <div className="h-[calc(100vh-6rem)] flex -m-6">
      {/* Optional Document Selection Panel */}
      <div className={`bg-slate-800 border-r border-slate-700 transition-all duration-300 overflow-hidden flex flex-col ${showDocsPanel ? 'w-80' : 'w-0'}`}>
        <div className="p-4 border-b border-slate-700">
          <h3 className="font-semibold text-white">Document Context</h3>
          <p className="text-xs text-slate-400 mt-1">Select documents to restrict the search context.</p>
        </div>
        <div className="flex-1 overflow-y-auto p-2">
          {allDocs.length === 0 ? (
            <p className="text-center text-sm text-slate-500 mt-4">No processed documents available.</p>
          ) : (
            allDocs.map(doc => (
              <div 
                key={doc.id} 
                onClick={() => toggleDocSelection(doc.id)}
                className={`p-3 mb-2 rounded-lg border cursor-pointer transition-colors text-sm ${selectedDocIds.includes(doc.id) ? 'bg-blue-600/20 border-blue-500' : 'bg-slate-900 border-slate-700 hover:border-slate-500'}`}
              >
                <div className="font-medium text-slate-200 truncate">{doc.original_filename}</div>
                <div className="text-xs text-slate-400 mt-1">{doc.company_name || '—'}</div>
              </div>
            ))
          )}
        </div>
      </div>

      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col min-w-0 bg-slate-900">
        <div className="h-12 border-b border-slate-700 flex items-center px-4 justify-between bg-slate-800/50">
          <button 
            onClick={() => setShowDocsPanel(!showDocsPanel)}
            className={`flex items-center gap-2 text-sm px-3 py-1.5 rounded-md transition-colors ${showDocsPanel ? 'bg-blue-600 text-white' : 'text-slate-400 hover:bg-slate-700 hover:text-white'}`}
          >
            <FileText size={16} />
            {selectedDocIds.length > 0 ? `${selectedDocIds.length} docs selected` : 'Context'}
          </button>
          {isStreaming && (
            <div className="flex items-center gap-2 text-xs text-slate-400">
              <Loader2 size={12} className="animate-spin text-blue-400" />
              <span>Gemini is researching...</span>
            </div>
          )}
        </div>

        <div className="flex-1 overflow-y-auto p-4 md:p-6 space-y-6">
          {messages.length === 0 ? (
            <div className="h-full flex flex-col items-center justify-center text-slate-500 space-y-4">
              <MessageSquare size={48} className="text-slate-700" />
              <p className="text-center">Ask a question about your financial documents to begin.</p>
              <p className="text-xs text-slate-600 text-center max-w-sm">
                Upload a document first (PDF, DOCX, or TXT), then ask questions like
                "What was the revenue growth?" or "Summarize the risk factors."
              </p>
            </div>
          ) : (
            messages.map((msg, idx) => (
              <MessageBubble 
                key={`${msg.id}-${idx}`}
                message={msg} 
                isLoading={isStreaming && idx === messages.length - 1 && msg.role === 'assistant' && msg.content === ''}
              />
            ))
          )}
          <div ref={messagesEndRef} />
        </div>

        <div className="p-4 bg-slate-800 border-t border-slate-700">
          <form onSubmit={handleSend} className="max-w-4xl mx-auto relative">
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Ask a question about your financial documents..."
              className="w-full bg-slate-900 border border-slate-600 rounded-xl pl-4 pr-12 py-3 focus:outline-none focus:border-blue-500 resize-none h-14 text-slate-200 placeholder-slate-500"
              rows={1}
              disabled={isStreaming}
            />
            <button 
              type="submit"
              disabled={!input.trim() || isStreaming}
              className="absolute right-2 top-2 p-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 transition-colors"
            >
              {isStreaming ? <Loader2 size={18} className="animate-spin" /> : <Send size={18} />}
            </button>
          </form>
          <div className="text-center mt-2">
            <span className="text-[10px] text-slate-500">AI can make mistakes. Verify important financial information.</span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ChatPage;
