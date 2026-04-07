import { create } from 'zustand';
import type { MessageRead, ConversationRead } from '../types/api';

interface ChatState {
  currentConversationId: string | null;
  messages: MessageRead[];
  isLoading: boolean;
  error: string | null;

  // Actions
  setConversation: (id: string | null) => void;
  setMessages: (messages: MessageRead[]) => void;
  addMessage: (message: MessageRead) => void;
  updateMessage: (id: string, updates: Partial<MessageRead>) => void;
  clearChat: () => void;
}

export const useChatStore = create<ChatState>((set) => ({
  currentConversationId: null,
  messages: [],
  isLoading: false,
  error: null,

  setConversation: (id) => set({ currentConversationId: id }),
  setMessages: (messages) => set({ messages }),
  addMessage: (message) => set((state) => ({ 
    messages: [...state.messages, message] 
  })),

  updateMessage: (id, updates) => set((state) => ({
    messages: state.messages.map((m) =>
      m.id === id ? { ...m, ...updates } : m
    ),
  })),

  clearChat: () => set({ currentConversationId: null, messages: [], error: null }),
}));
