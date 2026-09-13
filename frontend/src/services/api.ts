import axios from 'axios';
import { User, Document, Chat, Message } from '../types';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: API_BASE_URL,
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token && config.headers) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('token');
      // Only redirect if not already on login or register
      if (!window.location.pathname.includes('/login') && !window.location.pathname.includes('/register')) {
        window.location.href = '/login';
      }
    }
    return Promise.reject(error);
  }
);

// Auth
export const registerUser = (data: { email: string; password: string; full_name: string }) => 
  api.post<User>('/auth/register', data);

export const loginUser = (data: { email: string; password: string }) => 
  api.post<{ access_token: string; token_type: string }>('/auth/login', data);

export const getCurrentUser = () => api.get<User>('/users/me');

// Documents
export const uploadDocument = (formData: FormData) => 
  api.post<Document>('/documents/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  });

export const listDocuments = (filters?: { company_name?: string; document_type?: string }) => 
  api.get<Document[]>('/documents/', { params: filters });

export const getDocument = (id: number) => api.get<Document>(`/documents/${id}`);
export const deleteDocument = (id: number) => api.delete(`/documents/${id}`);

// Chats
export const createChat = (data: { title?: string; document_ids?: number[] }) => 
  api.post<Chat>('/chats/', data);

export const listChats = () => api.get<Chat[]>('/chats/');
export const getChatMessages = (chatId: number) => api.get<Message[]>(`/chats/${chatId}/messages`);

// SSE streaming
export const sendMessageStream = (chatId: number, content: string, documentIds?: number[]) => {
  const token = localStorage.getItem('token');
  return fetch(`${API_BASE_URL}/chats/${chatId}/messages`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`
    },
    body: JSON.stringify({ content, document_ids: documentIds })
  });
};

export default api;
