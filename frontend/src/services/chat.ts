import api from './api';
import type { 
  ConversationRead, 
  ConversationDetail, 
  QueryResponse 
} from '../types/api';

/**
 * Service for chat operations.
 * Note: Streaming SSE is handled via a custom hook (useChat).
 */
export const chatService = {
  /**
   * Create a new conversation for a specific document.
   */
  async createConversation(documentId: string, title = "Cuộc hội thoại mới"): Promise<ConversationRead> {
    const response = await api.post<ConversationRead>(`/chat/conversations/${documentId}`, {
      title,
    });
    return response.data;
  },

  /**
   * List conversations associated with a document.
   */
  async listConversations(documentId: string): Promise<ConversationRead[]> {
    const response = await api.get<ConversationRead[]>(`/chat/conversations/${documentId}`);
    return response.data;
  },

  /**
   * Get full message history for a conversation.
   */
  async getChatHistory(conversationId: string): Promise<ConversationDetail> {
    const response = await api.get<ConversationDetail>(`/chat/history/${conversationId}`);
    return response.data;
  },

  /**
   * Delete a conversation.
   */
  async deleteConversation(conversationId: string): Promise<{ status: string }> {
    const response = await api.delete<{ status: string }>(`/chat/conversations/${conversationId}`);
    return response.data;
  },

  /**
   * Legacy (non-SSE) chat endpoint. Use for simple one-off queries.
   */
  async chatLegacy(documentId: string, message: string, mode = "socratic"): Promise<QueryResponse> {
    const response = await api.post<QueryResponse>('/chat/socratic', {
      message,
    }, {
      params: { document_id: documentId, mode },
    });
    return response.data;
  },
};
