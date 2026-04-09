import { useState, useRef, useCallback, useEffect } from 'react';
import { useChatStore } from '../store/chat';
import { chatService } from '../services/chat';
import type { MessageRead } from '../types/api';
import { ErrorCode, isNetworkError } from '../types/errors';
import type { ChatErrorState } from '../types/errors';
import { ApiError } from '../services/api';
import { toast } from 'sonner';

interface ChatOptions {
  mode?: 'socratic' | 'feynman';
  conversationId?: string;
}

export function useChat() {
  const {
    messages,
    currentConversationId,
    setConversation,
    addMessage,
    updateMessage,
    setMessages,
    clearChat
  } = useChatStore();

  const [isStreaming, setIsStreaming] = useState(false);
  const abortControllerRef = useRef<AbortController | null>(null);

  // S8.1f: Error state for chat
  const [chatError, setChatError] = useState<ChatErrorState>({
    hasError: false,
    timestamp: 0,
  });

  // Store found_entities from last response
  const [lastFoundEntities, setLastFoundEntities] = useState<string[]>([]);

  // Load conversation history when conversation changes
  const loadConversationHistory = useCallback(async (conversationId: string) => {
    if (!conversationId) return;

    try {
      const history = await chatService.getChatHistory(conversationId);
      setMessages(history.messages);
    } catch (err: any) {
      console.error('Failed to load conversation history:', err);
      toast.error(`Không thể tải lịch sử: ${err.message}`);
    }
  }, [setMessages]);

  // Auto-load when conversation changes
  useEffect(() => {
    if (currentConversationId) {
      loadConversationHistory(currentConversationId);
    }
  }, [currentConversationId, loadConversationHistory]);

  const sendMessage = useCallback(async (
    message: string,
    mode: 'socratic' | 'feynman' = 'socratic',
    documentId?: string
  ) => {
    if (!documentId && !currentConversationId) {
       console.error("Missing documentId or conversationId");
       toast.error('Không thể gửi tin nhắn: thiếu thông tin tài liệu hoặc cuộc hội thoại');
       return;
    }

    // Clear previous error state
    setChatError({ hasError: false, timestamp: 0 });

    setIsStreaming(true);
    abortControllerRef.current = new AbortController();

    // 1. Optimistic Update: Add user message
    const userMsgId = crypto.randomUUID();
    const userMsg: MessageRead = {
      id: userMsgId,
      role: 'user',
      content: message,
      status: 'COMPLETED',
      created_at: new Date().toISOString(),
    };
    addMessage(userMsg);

    // 2. Prepare assistant placeholder
    const assistantMsgId = crypto.randomUUID();
    const assistantMsg: MessageRead = {
      id: assistantMsgId,
      role: 'assistant',
      content: '',
      status: 'PENDING',
      created_at: new Date().toISOString(),
    };
    addMessage(assistantMsg);

    const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1';

    let retryCount = 0;
    const MAX_RETRIES = 3;
    let hasReceivedMeta = false;

    // S8.1f: Timeout detection - 30 seconds
    let hasReceivedAnyChunk = false;
    let chunkTimeoutTimer: ReturnType<typeof setTimeout> | null = null;

    const startChunkTimeout = () => {
      // Clear existing timer
      if (chunkTimeoutTimer) {
        clearTimeout(chunkTimeoutTimer);
      }
      
      // Set 30s timeout to detect no response
      chunkTimeoutTimer = setTimeout(() => {
        if (!hasReceivedAnyChunk) {
          // S8.1f: AI not responding
          console.error('S8.1f: AI không phản hồi sau 30s');
          
          setChatError({
            hasError: true,
            errorCode: ErrorCode.AI_NO_RESPONSE,
            errorMessage: 'AI không phản hồi sau 30 giây. Có thể do API key, mạng, hoặc model đang quá tải.',
            messageId: assistantMsgId,
            timestamp: Date.now(),
          });
          
          updateMessage(assistantMsgId, {
            content: '⚠️ AI không phản hồi — thử lại nhé.',
            status: 'FAILED',
          });
          
          setIsStreaming(false);
          abortControllerRef.current?.abort();
        }
      }, 30000); // 30 seconds
    };
    
    const resetChunkTimeout = () => {
      if (chunkTimeoutTimer) {
        clearTimeout(chunkTimeoutTimer);
        chunkTimeoutTimer = null;
      }
    };

    while (retryCount <= MAX_RETRIES) {
      try {
        // Accumulator for assistant content — reset on each retry to avoid stale content
        let assistantContentAccumulator = '';

        // Start timeout before making request
        startChunkTimeout();
        
        const response = await fetch(`${API_BASE_URL}/chat/stream`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            document_id: documentId,
            conversation_id: currentConversationId,
            message: message,
            mode: mode
          }),
          signal: abortControllerRef.current.signal
        });

        if (!response.ok) {
          // S8.1a, S8.1d: Map HTTP status to error codes
          let errorCode: ErrorCode;
          let errorMessage = `HTTP Error: ${response.status}`;
          
          if (response.status === 504) {
            // S8.1a: LLM Timeout
            errorCode = ErrorCode.LLM_TIMEOUT;
            errorMessage = 'AI đang bận xử lý câu hỏi của bạn — thử lại nhé.';
          } else if (response.status === 401) {
            // S8.1d: Invalid API Key
            errorCode = ErrorCode.INVALID_API_KEY;
            errorMessage = 'API Key không hợp lệ. Vui lòng kiểm tra cài đặt.';
          } else {
            errorCode = ErrorCode.UNKNOWN_ERROR;
          }
          
          throw new ApiError(errorMessage, response.status, null, errorCode);
        }
        
        if (!response.body) throw new Error('ReadableStream not supported');

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });

          // Parse SSE format
          const lines = buffer.split('\n');
          buffer = lines.pop() || '';

          let currentEvent = '';

          for (const line of lines) {
            if (line.startsWith('event:')) {
              currentEvent = line.replace('event:', '').trim();
            } else if (line.startsWith('data:')) {
              const dataStr = line.replace('data:', '').trim();
              if (!dataStr) continue;

              try {
                const data = JSON.parse(dataStr);

                if (currentEvent === 'meta') {
                  hasReceivedMeta = true;
                  if (data.conversation_id) setConversation(data.conversation_id);
                } else if (currentEvent === 'chunk') {
                  // S8.1f: Mark that we received at least one chunk
                  hasReceivedAnyChunk = true;
                  resetChunkTimeout();

                  // Accumulate content locally to avoid repeated O(n) store lookups
                  assistantContentAccumulator += data.delta || '';
                  updateMessage(assistantMsgId, {
                    content: assistantContentAccumulator
                  });
                } else if (currentEvent === 'done') {
                  resetChunkTimeout();

                  // Save found_entities for ContextChips
                  if (data.found_entities && Array.isArray(data.found_entities)) {
                    setLastFoundEntities(data.found_entities);
                  }

                  updateMessage(assistantMsgId, {
                    content: data.content_full,
                    status: 'COMPLETED',
                    context_used: data.context_used
                  });
                  setIsStreaming(false);
                  return;
                } else if (currentEvent === 'error') {
                  resetChunkTimeout();
                  throw new Error(data.detail || 'Backend error');
                }
              } catch (e) {
                console.warn('Failed to parse SSE data chunk', e);
              }
            }
          }
        }
        break;
      } catch (err: any) {
        // Reset timeout on error
        resetChunkTimeout();
        
        if (err.name === 'AbortError') {
          setIsStreaming(false);
          return;
        }
        
        // Determine error type and set appropriate error state
        if (err instanceof ApiError) {
          // S8.1a, S8.1d: Handle specific API errors
          console.error(`Chat error: ${err.code} - ${err.message}`);
          
          setChatError({
            hasError: true,
            errorCode: err.code,
            errorMessage: err.message,
            messageId: assistantMsgId,
            timestamp: Date.now(),
          });
          
          updateMessage(assistantMsgId, {
            content: `Lỗi: ${err.message}`,
            status: 'FAILED',
          });
          
        } else if (isNetworkError(err)) {
          // S8.1e: Network failure
          console.error('S8.1e: Network error in chat');
          
          setChatError({
            hasError: true,
            errorCode: ErrorCode.NETWORK_ERROR,
            errorMessage: 'Mất kết nối mạng — kiểm tra lại và thử lại nhé',
            messageId: assistantMsgId,
            timestamp: Date.now(),
          });
          
          updateMessage(assistantMsgId, {
            content: 'Lỗi: Mất kết nối mạng',
            status: 'FAILED',
          });
          
        } else {
          // Generic error
          console.error('Chat error:', err);
          
          updateMessage(assistantMsgId, {
            content: `Lỗi: ${err.message}`,
            status: 'FAILED',
          });
        }

        // Retry logic - only retry if haven't received meta and under max retries
        if (!hasReceivedMeta && retryCount < MAX_RETRIES) {
          retryCount++;
          await new Promise(r => setTimeout(r, Math.pow(2, retryCount) * 1000));
          continue;
        }
        
        break;
      }
    }
    setIsStreaming(false);
  }, [currentConversationId, addMessage, updateMessage, setConversation]);

  const abort = useCallback(() => {
    abortControllerRef.current?.abort();
  }, []);
  
  // S8.1f: Clear error state
  const clearError = useCallback(() => {
    setChatError({ hasError: false, timestamp: 0 });
    setLastFoundEntities([]);
  }, []);

  // Create new conversation
  const createNewConversation = useCallback(async (documentId: string) => {
    try {
      const conv = await chatService.createConversation(documentId);
      setConversation(conv.id);
      clearChat();
      setLastFoundEntities([]);
      toast.success('Đã tạo cuộc hội thoại mới');
      return conv.id;
    } catch (err: any) {
      toast.error(`Không thể tạo cuộc hội thoại: ${err.message}`);
      return null;
    }
  }, [setConversation, clearChat]);

  return {
    messages,
    sendMessage,
    isStreaming,
    abort,
    // S8.1a, S8.1e, S8.1f: Export error state and clear function
    chatError,
    clearError,
    // Context entities from last response
    lastFoundEntities,
    // Conversation management
    currentConversationId,
    createNewConversation,
    setConversation,
    loadConversationHistory,
  };
}
