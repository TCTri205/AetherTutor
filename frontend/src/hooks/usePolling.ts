import { useEffect, useRef, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useDocumentStore } from '../store/document';
import { documentService } from '../services/documents';
import { chatService } from '../services/chat';
import { ApiError } from '../services/api';
import { toast } from 'sonner';

interface UsePollingOptions {
  /** Callback khi document COMPLETED */
  onComplete?: (documentId: string) => void;
  /** Document ID để sync conversation title (optional) */
  conversationId?: string | null;
  /** Callback khi title được update */
  onTitleUpdated?: (title: string) => void;
}

/**
 * Hook to poll document status until it's finished processing.
 * Also handles redirection if document is deleted (404).
 * Includes Conversation Title Sync: polls 5 times after COMPLETED to wait for backend title generation.
 */
export function usePolling(documentId: string | undefined, options?: UsePollingOptions) {
  const navigate = useNavigate();
  const { updateDocumentStatus } = useDocumentStore();
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const titlePollTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const stopPolling = useCallback(() => {
    if (timerRef.current) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }
    if (titlePollTimerRef.current) {
      clearInterval(titlePollTimerRef.current);
      titlePollTimerRef.current = null;
    }
  }, []);

  useEffect(() => {
    if (!documentId) return;

    let titleSyncAttempts = 0;
    const MAX_TITLE_SYNC_ATTEMPTS = 5;
    const TITLE_SYNC_INTERVAL = 3000; // 3s

    const poll = async () => {
      try {
        const doc = await documentService.getDocumentStatus(documentId);
        updateDocumentStatus(documentId, doc);

        // Stop polling if finished
        if (doc.status === 'COMPLETED' || doc.status === 'FAILED') {
          stopPolling();

          // Fire onComplete callback
          if (options?.onComplete && doc.status === 'COMPLETED') {
            options.onComplete(documentId);
          }

          // S6.6: Conversation Title Sync
          // Nếu có conversationId, poll thêm 5 lần để đợi backend generate title
          if (options?.conversationId && doc.status === 'COMPLETED') {
            const convId = options.conversationId;
            let originalTitle: string | null = null;

            titlePollTimerRef.current = setInterval(async () => {
              titleSyncAttempts++;

              try {
                const conversations = await chatService.listConversations(documentId);
                const currentConv = conversations.find(c => c.id === convId);

                if (currentConv) {
                  // Lưu title ban đầu để so sánh
                  if (!originalTitle) {
                    originalTitle = currentConv.title;
                  }

                  // Nếu title thay đổi từ "Cuộc hội thoại mới" → giá trị khác
                  if (currentConv.title &&
                      currentConv.title !== 'Cuộc hội thoại mới' &&
                      currentConv.title !== originalTitle) {
                    // Title đã được generate
                    stopPolling();
                    toast.success(`Đã đặt tên: "${currentConv.title}"`);
                    if (options?.onTitleUpdated) {
                      options.onTitleUpdated(currentConv.title);
                    }
                  }
                }

                // Stop sau 5 attempts hoặc 15s timeout
                if (titleSyncAttempts >= MAX_TITLE_SYNC_ATTEMPTS) {
                  stopPolling();
                  console.log('Title sync timeout sau 15s — dùng fallback title');
                }
              } catch (err) {
                console.warn('Title sync poll error:', err);
              }
            }, TITLE_SYNC_INTERVAL);
          }

          return;
        }
      } catch (err: any) {
        if (err instanceof ApiError && err.status === 404) {
          console.error('Document not found or deleted. Redirecting...');
          stopPolling();
          toast.error('Tài liệu này đã bị xóa.');
          navigate('/vault');
        }
      }
    };

    // Initial check
    poll();

    // Set interval
    timerRef.current = setInterval(poll, 3000);

    return () => {
      stopPolling();
    };
  }, [documentId, updateDocumentStatus, navigate, options?.conversationId, options?.onComplete, options?.onTitleUpdated, stopPolling]);

  return { stopPolling };
}
