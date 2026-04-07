/**
 * Unit Tests cho Phase 5 - AetherTutor Frontend
 * Covers: Error types, State management, SSE parser, API client
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { ErrorCode, getErrorMessage, mapHttpStatusToErrorCode, isNetworkError, isRetryable } from '../types/errors';
import { ApiError } from '../services/api';

// ─── Error Types Tests ───────────────────────────────────────────
describe('Error Types & Helpers', () => {
  describe('ErrorCode constants', () => {
    it('should define all expected error codes', () => {
      expect(ErrorCode.FILE_TOO_LARGE).toBe('FILE_TOO_LARGE');
      expect(ErrorCode.SCANNED_PDF).toBe('SCANNED_PDF');
      expect(ErrorCode.INVALID_FILE_FORMAT).toBe('INVALID_FILE_FORMAT');
      expect(ErrorCode.LLM_TIMEOUT).toBe('LLM_TIMEOUT');
      expect(ErrorCode.AI_NO_RESPONSE).toBe('AI_NO_RESPONSE');
      expect(ErrorCode.INVALID_API_KEY).toBe('INVALID_API_KEY');
      expect(ErrorCode.NETWORK_ERROR).toBe('NETWORK_ERROR');
      expect(ErrorCode.SERVER_ERROR).toBe('SERVER_ERROR');
      expect(ErrorCode.INVALID_RESPONSE_FORMAT).toBe('INVALID_RESPONSE_FORMAT');
      expect(ErrorCode.UNKNOWN_ERROR).toBe('UNKNOWN_ERROR');
    });
  });

  describe('getErrorMessage', () => {
    it('should return correct message for FILE_TOO_LARGE', () => {
      const msg = getErrorMessage(ErrorCode.FILE_TOO_LARGE);
      expect(msg.title).toBe('File quá lớn');
      expect(msg.code).toBe(ErrorCode.FILE_TOO_LARGE);
    });

    it('should return correct message for LLM_TIMEOUT', () => {
      const msg = getErrorMessage(ErrorCode.LLM_TIMEOUT);
      expect(msg.title).toBe('AI đang bận xử lý');
      expect(msg.suggestion).toBe('Model đang quá tải hoặc kết nối chậm.');
    });

    it('should return correct message for AI_NO_RESPONSE', () => {
      const msg = getErrorMessage(ErrorCode.AI_NO_RESPONSE);
      expect(msg.title).toBe('⚠️ AI không phản hồi');
      expect(msg.code).toBe(ErrorCode.AI_NO_RESPONSE);
    });

    it('should return correct message for INVALID_API_KEY', () => {
      const msg = getErrorMessage(ErrorCode.INVALID_API_KEY);
      expect(msg.title).toBe('API Key không hợp lệ');
      expect(msg.suggestion).toBe('Kiểm tra file .env hoặc Settings.');
    });

    it('should override message with detail if provided', () => {
      const customDetail = 'Custom error detail';
      const msg = getErrorMessage(ErrorCode.UNKNOWN_ERROR, customDetail);
      expect(msg.message).toBe(customDetail);
    });

    it('should return default message when no detail provided', () => {
      const msg = getErrorMessage(ErrorCode.NETWORK_ERROR);
      expect(msg.message).toContain('Không thể kết nối');
    });
  });

  describe('mapHttpStatusToErrorCode', () => {
    it('should map 401 to INVALID_API_KEY', () => {
      expect(mapHttpStatusToErrorCode(401)).toBe(ErrorCode.INVALID_API_KEY);
    });

    it('should map 413 to FILE_TOO_LARGE', () => {
      expect(mapHttpStatusToErrorCode(413)).toBe(ErrorCode.FILE_TOO_LARGE);
    });

    it('should map 504 to LLM_TIMEOUT', () => {
      expect(mapHttpStatusToErrorCode(504)).toBe(ErrorCode.LLM_TIMEOUT);
    });

    it('should map 500/502/503 to SERVER_ERROR', () => {
      expect(mapHttpStatusToErrorCode(500)).toBe(ErrorCode.SERVER_ERROR);
      expect(mapHttpStatusToErrorCode(502)).toBe(ErrorCode.SERVER_ERROR);
      expect(mapHttpStatusToErrorCode(503)).toBe(ErrorCode.SERVER_ERROR);
    });

    it('should map unknown status to UNKNOWN_ERROR', () => {
      expect(mapHttpStatusToErrorCode(404)).toBe(ErrorCode.UNKNOWN_ERROR);
      expect(mapHttpStatusToErrorCode(418)).toBe(ErrorCode.UNKNOWN_ERROR);
    });
  });

  describe('isNetworkError', () => {
    it('should detect network error by code', () => {
      expect(isNetworkError({ code: 'NETWORK_ERROR' })).toBe(true);
      expect(isNetworkError({ code: ErrorCode.NETWORK_ERROR })).toBe(true);
    });

    it('should detect network error by message', () => {
      expect(isNetworkError({ message: 'Network Error' })).toBe(true);
    });

    it('should detect network error by status 0', () => {
      expect(isNetworkError({ status: 0 })).toBe(true);
    });

    it('should return false for non-network errors', () => {
      expect(isNetworkError({ code: ErrorCode.LLM_TIMEOUT })).toBe(false);
      expect(isNetworkError({ message: 'Some other error' })).toBe(false);
    });
  });

  describe('isRetryable', () => {
    it('should allow retry for LLM_TIMEOUT', () => {
      expect(isRetryable({ code: ErrorCode.LLM_TIMEOUT })).toBe(true);
    });

    it('should allow retry for NETWORK_ERROR', () => {
      expect(isRetryable({ code: ErrorCode.NETWORK_ERROR })).toBe(true);
    });

    it('should allow retry for AI_NO_RESPONSE', () => {
      expect(isRetryable({ code: ErrorCode.AI_NO_RESPONSE })).toBe(true);
    });

    it('should NOT allow retry for FILE_TOO_LARGE', () => {
      expect(isRetryable({ code: ErrorCode.FILE_TOO_LARGE })).toBe(false);
    });

    it('should NOT allow retry for SCANNED_PDF', () => {
      expect(isRetryable({ code: ErrorCode.SCANNED_PDF })).toBe(false);
    });

    it('should NOT allow retry for INVALID_API_KEY', () => {
      expect(isRetryable({ code: ErrorCode.INVALID_API_KEY })).toBe(false);
    });
  });
});

// ─── ApiError Class Tests ────────────────────────────────────────
describe('ApiError', () => {
  it('should create error with all properties', () => {
    const err = new ApiError('Test error', 500, { detail: 'x' }, ErrorCode.SERVER_ERROR);
    expect(err.name).toBe('ApiError');
    expect(err.message).toBe('Test error');
    expect(err.status).toBe(500);
    expect(err.data).toEqual({ detail: 'x' });
    expect(err.code).toBe(ErrorCode.SERVER_ERROR);
  });

  it('should work with minimal properties', () => {
    const err = new ApiError('Simple error');
    expect(err.message).toBe('Simple error');
    expect(err.status).toBeUndefined();
    expect(err.code).toBeUndefined();
  });
});

// ─── Zustand Store Tests ─────────────────────────────────────────
describe('Chat Store', () => {
  // Import inside describe to avoid side effects
  let useChatStore: any;

  beforeEach(async () => {
    // Reset store before each test
    const mod = await import('../store/chat');
    useChatStore = mod.useChatStore;
    useChatStore.setState({
      currentConversationId: null,
      messages: [],
      isLoading: false,
      error: null,
    });
  });

  it('should have initial state', () => {
    const state = useChatStore.getState();
    expect(state.currentConversationId).toBeNull();
    expect(state.messages).toEqual([]);
    expect(state.isLoading).toBe(false);
    expect(state.error).toBeNull();
  });

  it('should set conversation', () => {
    useChatStore.getState().setConversation('conv-123');
    expect(useChatStore.getState().currentConversationId).toBe('conv-123');
  });

  it('should add message', () => {
    const msg = { id: 'msg-1', role: 'user' as const, content: 'Hello', status: 'COMPLETED' as const, created_at: '2024-01-01' };
    useChatStore.getState().addMessage(msg);
    expect(useChatStore.getState().messages).toHaveLength(1);
    expect(useChatStore.getState().messages[0].content).toBe('Hello');
  });

  it('should update message', () => {
    const msg = { id: 'msg-1', role: 'assistant' as const, content: '', status: 'PENDING' as const, created_at: '2024-01-01' };
    useChatStore.getState().addMessage(msg);
    useChatStore.getState().updateMessage('msg-1', { content: 'Updated', status: 'COMPLETED' });
    const updated = useChatStore.getState().messages.find((m: any) => m.id === 'msg-1');
    expect(updated?.content).toBe('Updated');
    expect(updated?.status).toBe('COMPLETED');
  });

  it('should clear chat', () => {
    useChatStore.getState().setConversation('conv-123');
    useChatStore.getState().addMessage({ id: 'msg-1', role: 'user' as const, content: 'Hi', status: 'COMPLETED' as const, created_at: '2024-01-01' });
    useChatStore.getState().clearChat();
    const state = useChatStore.getState();
    expect(state.currentConversationId).toBeNull();
    expect(state.messages).toEqual([]);
    expect(state.error).toBeNull();
  });

  it('should set messages array', () => {
    const msgs = [
      { id: '1', role: 'user' as const, content: 'Hi', status: 'COMPLETED' as const, created_at: '2024-01-01' },
      { id: '2', role: 'assistant' as const, content: 'Hello!', status: 'COMPLETED' as const, created_at: '2024-01-01' },
    ];
    useChatStore.getState().setMessages(msgs);
    expect(useChatStore.getState().messages).toHaveLength(2);
  });
});

describe('Document Store', () => {
  let useDocumentStore: any;

  beforeEach(async () => {
    const mod = await import('../store/document');
    useDocumentStore = mod.useDocumentStore;
    useDocumentStore.setState({ documents: [], isLoading: false, error: null });
  });

  it('should have initial state', () => {
    const state = useDocumentStore.getState();
    expect(state.documents).toEqual([]);
    expect(state.isLoading).toBe(false);
    expect(state.error).toBeNull();
  });

  it('should update document status', () => {
    const doc = { id: 'doc-1', filename: 'test.pdf', status: 'PROCESSING' as const, processing_step: 'EXTRACTING' as const, entity_count: 0, relation_count: 0, page_count: null, file_size: null, created_at: '2024-01-01', updated_at: '2024-01-01', error_message: null };
    useDocumentStore.setState({ documents: [doc] });
    useDocumentStore.getState().updateDocumentStatus('doc-1', { status: 'COMPLETED' });
    const updated = useDocumentStore.getState().documents.find((d: any) => d.id === 'doc-1');
    expect(updated?.status).toBe('COMPLETED');
  });

  it('should remove document', () => {
    const doc = { id: 'doc-1', filename: 'test.pdf', status: 'COMPLETED' as const, processing_step: 'COMPLETED' as const, entity_count: 0, relation_count: 0, page_count: null, file_size: null, created_at: '2024-01-01', updated_at: '2024-01-01', error_message: null };
    useDocumentStore.setState({ documents: [doc] });
    useDocumentStore.getState().removeDocument('doc-1');
    expect(useDocumentStore.getState().documents).toHaveLength(0);
  });
});

describe('UI Store', () => {
  let useUIStore: any;

  beforeEach(async () => {
    const mod = await import('../store/ui');
    useUIStore = mod.useUIStore;
  });

  it('should have initial state', () => {
    const state = useUIStore.getState();
    expect(state.sidebarCollapsed).toBe(false);
    expect(state.mobileMenuOpen).toBe(false);
    expect(state.isDark).toBe(true);
    expect(state.llmMode).toBe('unknown');
  });

  it('should toggle sidebar', () => {
    useUIStore.getState().toggleSidebar();
    expect(useUIStore.getState().sidebarCollapsed).toBe(true);
    useUIStore.getState().toggleSidebar();
    expect(useUIStore.getState().sidebarCollapsed).toBe(false);
  });

  it('should set mobile menu open', () => {
    useUIStore.getState().setMobileMenuOpen(true);
    expect(useUIStore.getState().mobileMenuOpen).toBe(true);
  });

  it('should toggle theme', () => {
    useUIStore.getState().toggleTheme();
    expect(useUIStore.getState().isDark).toBe(false);
  });

  it('should set LLM info', () => {
    useUIStore.getState().setLlmInfo({ mode: 'cloud', provider: 'openai', model: 'gpt-4' });
    const state = useUIStore.getState();
    expect(state.llmMode).toBe('cloud');
    expect(state.llmProvider).toBe('openai');
    expect(state.llmModel).toBe('gpt-4');
  });
});

// ─── SSE Parser Logic Tests ──────────────────────────────────────
describe('SSE Parser (extracted logic)', () => {
  /**
   * Parse SSE buffer — same logic as in useChat hook
   */
  function parseSSEBuffer(buffer: string): Array<{ event: string; data: any }> {
    const events: Array<{ event: string; data: any }> = [];
    const lines = buffer.split('\n');
    let currentEvent = '';
    let remainingBuffer = '';

    for (const line of lines) {
      if (line.startsWith('event:')) {
        currentEvent = line.replace('event:', '').trim();
      } else if (line.startsWith('data:')) {
        const dataStr = line.replace('data:', '').trim();
        if (!dataStr) continue;

        try {
          const data = JSON.parse(dataStr);
          events.push({ event: currentEvent, data });
        } catch {
          // Invalid JSON — skip
        }
      }
    }

    remainingBuffer = lines.pop() || '';

    return events;
  }

  it('should parse meta event', () => {
    const buffer = 'event: meta\ndata: {"conversation_id": "conv-1", "message_id": "msg-1"}\n\n';
    const events = parseSSEBuffer(buffer);
    expect(events).toHaveLength(1);
    expect(events[0].event).toBe('meta');
    expect(events[0].data.conversation_id).toBe('conv-1');
  });

  it('should parse chunk event', () => {
    const buffer = 'event: chunk\ndata: {"delta": "Hello"}\n\n';
    const events = parseSSEBuffer(buffer);
    expect(events).toHaveLength(1);
    expect(events[0].event).toBe('chunk');
    expect(events[0].data.delta).toBe('Hello');
  });

  it('should parse done event with found_entities', () => {
    const buffer = 'event: done\ndata: {"content_full": "Answer", "found_entities": ["Entity1", "Entity2"]}\n\n';
    const events = parseSSEBuffer(buffer);
    expect(events).toHaveLength(1);
    expect(events[0].event).toBe('done');
    expect(events[0].data.content_full).toBe('Answer');
    expect(events[0].data.found_entities).toEqual(['Entity1', 'Entity2']);
  });

  it('should parse error event', () => {
    const buffer = 'event: error\ndata: {"detail": "LLM unavailable"}\n\n';
    const events = parseSSEBuffer(buffer);
    expect(events).toHaveLength(1);
    expect(events[0].event).toBe('error');
    expect(events[0].data.detail).toBe('LLM unavailable');
  });

  it('should parse multiple events in one buffer', () => {
    const buffer = 'event: meta\ndata: {"conversation_id": "c1"}\n\nevent: chunk\ndata: {"delta": "Hi"}\n\nevent: chunk\ndata: {"delta": " there"}\n\n';
    const events = parseSSEBuffer(buffer);
    expect(events).toHaveLength(3);
    expect(events[0].event).toBe('meta');
    expect(events[1].data.delta).toBe('Hi');
    expect(events[2].data.delta).toBe(' there');
  });

  it('should handle fragmented buffer (partial line at end)', () => {
    const buffer = 'event: chunk\ndata: {"delta": "Hel';
    const events = parseSSEBuffer(buffer);
    expect(events).toHaveLength(0); // Incomplete JSON, should be skipped
  });

  it('should handle empty data lines', () => {
    const buffer = 'event: chunk\ndata: \n\n';
    const events = parseSSEBuffer(buffer);
    expect(events).toHaveLength(0);
  });

  it('should handle reasoning event', () => {
    const buffer = 'event: reasoning\ndata: {"delta": "Thinking..."}\n\n';
    const events = parseSSEBuffer(buffer);
    expect(events).toHaveLength(1);
    expect(events[0].event).toBe('reasoning');
    expect(events[0].data.delta).toBe('Thinking...');
  });
});
