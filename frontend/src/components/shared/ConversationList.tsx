import '../styles/tokens.css';
import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Plus,
  Trash2,
  MessageSquare,
  Loader2,
  MoreVertical,
  Check
} from 'lucide-react';
import { chatService } from '../../services/chat';
import type { ConversationRead } from '../../types/api';
import { cn } from '../../lib/utils';
import { toast } from 'sonner';

interface ConversationListProps {
  documentId: string;
  activeConversationId: string | null;
  onSelectConversation: (id: string) => void;
  onNewConversation: () => void;
}

export default function ConversationList({
  documentId,
  activeConversationId,
  onSelectConversation,
  onNewConversation,
}: ConversationListProps) {
  const [conversations, setConversations] = useState<ConversationRead[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [deletingId, setDeletingId] = useState<string | null>(null);

  // Fetch conversations on mount + document change
  useEffect(() => {
    fetchConversations();
  }, [documentId]);

  const fetchConversations = async () => {
    setIsLoading(true);
    try {
      const list = await chatService.listConversations(documentId);
      // Sort by created_at descending (newest first)
      list.sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());
      setConversations(list);
    } catch (err: any) {
      console.error('Failed to fetch conversations:', err);
      // Don't show toast for this error - let parent handle it
    } finally {
      setIsLoading(false);
    }
  };

  const handleDelete = async (e: React.MouseEvent, convId: string) => {
    e.stopPropagation();
    setDeletingId(convId);
    try {
      await chatService.deleteConversation(convId);
      setConversations((prev) => prev.filter((c) => c.id !== convId));
      toast.success('Đã xóa cuộc hội thoại');

      // If deleted active conversation, create new one
      if (convId === activeConversationId) {
        onNewConversation();
      }
    } catch (err: any) {
      toast.error(`Không thể xóa: ${err.message}`);
    } finally {
      setDeletingId(null);
    }
  };

  const getTitle = (conv: ConversationRead, index: number) => {
    // Fallback title nếu title null hoặc generic
    if (!conv.title || conv.title === 'Cuộc hội thoại mới') {
      return `Hội thoại #${index + 1}`;
    }
    return conv.title;
  };

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="px-4 py-3 border-b border-border-primary">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-xs font-bold text-secondary uppercase tracking-widest">
            Cuộc hội thoại
          </h3>
          <button
            onClick={onNewConversation}
            className="p-1.5 rounded-lg bg-primary/10 hover:bg-primary/20 text-primary transition-colors"
            title="Tạo cuộc hội thoại mới"
          >
            <Plus className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* List */}
      <div className="flex-1 overflow-y-auto py-2">
        {isLoading ? (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="w-4 h-4 animate-spin text-muted-foreground" />
          </div>
        ) : conversations.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-8 px-4 text-center">
            <MessageSquare className="w-8 h-8 text-tertiary mb-2" />
            <p className="text-xs text-secondary">
              Chưa có cuộc hội thoại nào
            </p>
          </div>
        ) : (
          <div className="space-y-1 px-2">
            <AnimatePresence mode="popLayout">
              {conversations.map((conv, index) => {
                const isActive = conv.id === activeConversationId;
                const isDeleting = deletingId === conv.id;

                return (
                  <motion.div
                    key={conv.id}
                    layout
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, height: 0 }}
                    transition={{ duration: 0.2 }}
                  >
                    <motion.button
                      role="button"
                      aria-disabled={isDeleting}
                      onClick={() => !isDeleting && onSelectConversation(conv.id)}
                      onKeyDown={(e) => {
                        if (!isDeleting && (e.key === 'Enter' || e.key === ' ')) {
                          e.preventDefault();
                          onSelectConversation(conv.id);
                        }
                      }}
                      className={cn(
                        "w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-left transition-all group relative cursor-pointer",
                        isActive
                          ? "bg-primary/10 text-primary border border-primary/20"
                          : "text-secondary hover:bg-secondary hover:text-primary border border-transparent",
                        isDeleting && "opacity-50 pointer-events-none"
                      )}
                    >
                      {/* Icon */}
                      <div className={cn(
                        "w-8 h-8 rounded-lg flex items-center justify-center shrink-0",
                        isActive
                          ? "bg-primary/20 text-primary"
                          : "bg-secondary text-secondary group-hover:text-primary"
                      )}>
                        {isDeleting ? (
                          <Loader2 className="w-4 h-4 animate-spin" />
                        ) : (
                          <MessageSquare className="w-4 h-4" />
                        )}
                      </div>

                      {/* Title */}
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium truncate">
                          {getTitle(conv, index)}
                        </p>
                        <p className="text-[10px] text-secondary/60">
                          {new Date(conv.created_at).toLocaleDateString('vi-VN')}
                        </p>
                      </div>

                      {/* Delete Button */}
                      {!isActive && (
                        <button
                          onClick={(e) => handleDelete(e, conv.id)}
                          className="absolute right-2 top-2 p-1 rounded-md opacity-0 group-hover:opacity-100 hover:bg-red-500/20 hover:text-red-500 transition-all"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      )}

                      {/* Active Indicator */}
                      {isActive && (
                        <Check className="w-4 h-4 text-primary shrink-0" />
                      )}
                    </motion.button>
                  </motion.div>
                );
              })}
            </AnimatePresence>
          </div>
        )}
      </div>

      {/* Footer Stats */}
      {conversations.length > 0 && (
        <div className="px-4 py-2 border-t border-border-primary">
          <p className="text-[10px] text-secondary text-center">
            {conversations.length} cuộc hội thoại
          </p>
        </div>
      )}
    </div>
  );
}
