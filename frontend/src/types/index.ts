export interface User {
  id: number;
  email: string;
  full_name: string;
  is_active: boolean;
  created_at: string;
}

export interface Document {
  id: number;
  filename: string;
  original_filename: string;
  file_type: string;
  file_size_bytes: number;
  company_name: string | null;
  ticker: string | null;
  document_type: string | null;
  reporting_period: string | null;
  fiscal_year: string | null;
  status: 'processing' | 'ready' | 'failed';
  num_chunks: number;
  error_message: string | null;
  created_at: string;
}

export interface Citation {
  document_name: string;
  page_number: number | null;
  section_title: string | null;
  chunk_index: number;
  relevance_score: number;
  content_snippet: string;
}

export interface Message {
  id: number;
  chat_id: number;
  role: 'user' | 'assistant';
  content: string;
  sources: Citation[];
  created_at: string;
}

export interface Chat {
  id: number;
  title: string | null;
  document_ids: number[] | null;
  created_at: string;
  updated_at: string;
}

export interface StreamEvent {
  token?: string;
  citations?: Citation[];
  done?: boolean;
  error?: string;
}
