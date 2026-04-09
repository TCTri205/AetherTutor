import { useState, useRef, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { Send, Sparkles, Brain, Loader2, Star, PanelLeftClose, PanelLeftOpen } from 'lucide-react';
import { useDocumentStore } from '../store/document';
import { useChat } from '../hooks/useChat';
import { Button } from '../components/ui/Button';
import ChatHeader from '../components/shared/ChatHeader';
import ChatMessage from '../components/shared/ChatMessage';
import ChatErrorCard from '../components/shared/ChatErrorCard';
import ConversationList from '../components/shared/ConversationList';
import ContextChips from '../components/shared/ContextChips';
import { cn } from '../lib/utils';
import { toast } from 'sonner';

export default function Chat() {
  const { documentId } = useParams<{ documentId: string }>();
  const { documents } = useDocumentStore();
  const [input, setInput] = useState('');
  const [mode, setMode] = useState<'socratic' | 'feynman'>('feynman');
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const scrollRef = useRef<HTMLDivElement>(null);

  const doc = documents.find((d) => d.id === documentId);
  const {
    messages,
    sendMessage,
    isStreaming,
    chatError,
    clearError,
    lastFoundEntities,
    currentConversationId,
    createNewConversation,
    setConversation,
  } = useChat();

  // Auto scroll to bottom
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  const handleSend = async () => {
    if (!input.trim() || isStreaming) return;

    setInput('');
    try {
      await sendMessage(input, mode, documentId!);
    } catch (err: any) {
      toast.error(`Lỗi gửi tin nhắn: ${err.message}`);
    }
  };

  // S8.1a, S8.1e, S8.1f: Handle retry from error card
  const handleRetry = async () => {
    clearError();
    // Get last user message and retry
    const lastUserMessage = messages.filter(m => m.role === 'user').pop();
    if (lastUserMessage) {
      await sendMessage(lastUserMessage.content, mode, documentId!);
    }
  };

  const handleSelectConversation = (convId: string) => {
    // Clear error when switching conversations
    clearError();
    // Set current conversation ID in store
    // useEffect in useChat will auto-load history via currentConversationId watch
    setConversation(convId);
  };

  const handleNewConversation = async () => {
    if (documentId) {
      await createNewConversation(documentId);
    }
  };

  if (!doc) return null; // Handled by DocumentGuard but safe check

  return (
    <div className="flex h-full overflow-hidden bg-[#020617] rounded-3xl border border-white/5 relative">
      {/* Conversation List Sidebar */}
      {sidebarOpen && (
        <div className="w-64 border-r border-white/5 bg-black/20 flex flex-col shrink-0">
          <ConversationList
            documentId={documentId!}
            activeConversationId={currentConversationId}
            onSelectConversation={handleSelectConversation}
            onNewConversation={handleNewConversation}
          />
        </div>
      )}

      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Toggle Sidebar Button */}
        <button
          onClick={() => setSidebarOpen(!sidebarOpen)}
          aria-label={sidebarOpen ? "Hide conversation list" : "Show conversation list"}
          className="absolute left-2 top-20 z-20 p-2 rounded-xl bg-white/5 border border-white/10 hover:bg-white/10 transition-colors"
        >
          {sidebarOpen ? (
            <PanelLeftClose className="w-4 h-4 text-muted-foreground" />
          ) : (
            <PanelLeftOpen className="w-4 h-4 text-muted-foreground" />
          )}
        </button>

        <ChatHeader
          documentId={documentId!}
          filename={doc.filename}
          mode={mode}
          setMode={setMode}
        />

        {/* Messages Area */}
        <div
          ref={scrollRef}
          role="log"
          aria-label="Chat messages"
          aria-live="polite"
          className="flex-1 overflow-y-auto scroll-smooth py-4 flex flex-col items-center"
        >
          <div className="w-full">
            {/* Welcome/Empty State */}
            {messages.length === 0 && (
              <div className="flex flex-col items-center justify-center py-20 px-8 text-center max-w-2xl mx-auto space-y-8 animate-in fade-in slide-in-from-bottom-5 duration-700">
                 <div className="w-20 h-20 rounded-3xl bg-primary/10 flex items-center justify-center border border-primary/20 shadow-2xl shadow-primary/10 group relative">
                    <Brain className="w-10 h-10 text-primary group-hover:scale-110 transition-transform" />
                    <Sparkles className="absolute -top-2 -right-2 w-6 h-6 text-amber-400 animate-pulse" />
                 </div>
                 <div className="space-y-4">
                    <h3 className="text-3xl font-bold text-white tracking-tight">Xin chào, tôi là AI Tutor của bạn</h3>
                    <p className="text-muted-foreground leading-relaxed text-lg italic">
                      "Giáo dục là việc thắp sáng một ngọn lửa, không phải là việc làm đầy một chiếc bình."
                    </p>
                    <p className="text-muted-foreground text-sm max-w-md mx-auto">
                      Tôi đã chuẩn bị sẵn sàng kiến thức từ tài liệu <b>"{doc.filename}"</b>. Hãy bắt đầu cuộc hội thoại!
                    </p>
                 </div>
              </div>
            )}

            {/* Message List */}
            <div className="space-y-0">
              {messages.map((msg, i) => {
                // Find entities for this specific assistant message
                const msgEntities = msg.context_used?.found_entities || lastFoundEntities;

                return (
                  <div key={msg.id || i}>
                    <ChatMessage
                      role={msg.role === 'system' ? 'assistant' : msg.role}
                      content={msg.content}
                      reasoning={msg.reasoning}
                      isStreaming={isStreaming && i === messages.length - 1 && msg.role === 'assistant'}
                    />
                    {/* S6.3: ContextChips - Show entities from retrieval */}
                    {msg.role === 'assistant' && msg.status === 'COMPLETED' && msgEntities && msgEntities.length > 0 && (
                      <div className="max-w-4xl mx-auto px-4 md:px-8">
                        <ContextChips
                          entities={msgEntities}
                          documentId={documentId!}
                        />
                      </div>
                    )}
                  </div>
                );
              })}
            </div>

            {/* S8.1a, S8.1e, S8.1f: Error Card */}
            {chatError.hasError && (
              <div className="max-w-3xl mx-auto w-full px-4 py-6">
                <ChatErrorCard
                  error={chatError}
                  onRetry={handleRetry}
                  onGoToSettings={() => {
                    toast.info('Settings page coming soon in v2', { duration: 2000 });
                  }}
                />
              </div>
            )}
          </div>
        </div>

        {/* Input Area */}
        <div className="p-6 border-t border-white/5 glass-dark z-10 shrink-0">
          <div className="max-w-4xl mx-auto relative group">
            <textarea
              rows={1}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault();
                  handleSend();
                }
              }}
              placeholder={mode === 'socratic' ? "Yêu cầu Tutor đặt câu hỏi gợi mở..." : "Hỏi để được giải thích theo phong cách Feynman..."}
              aria-label="Type your message"
              aria-describedby="chat-input-hint"
              className="w-full bg-white/5 border border-white/10 rounded-2xl py-4 pr-14 pl-12 text-sm text-white focus:outline-none focus:ring-2 focus:ring-primary/40 focus:border-primary/50 transition-all resize-none group-focus-within:bg-white/10"
              style={{ minHeight: '56px', maxHeight: '200px' }}
            />
            <div className="absolute left-4 top-4">
               <div className={cn("w-6 h-6 rounded-full flex items-center justify-center transition-colors", mode === 'socratic' ? "bg-primary/20 text-primary" : "bg-amber-500/20 text-amber-500")}>
                  {mode === 'socratic' ? <Sparkles className="w-3.5 h-3.5" /> : <Star className="w-3.5 h-3.5" />}
               </div>
            </div>
            <Button
              size="icon"
              className="absolute right-2 top-2 rounded-xl h-10 w-10 shadow-lg shadow-primary/20"
              disabled={!input.trim() || isStreaming}
              onClick={handleSend}
            >
              {isStreaming ? (
                <Loader2 className="w-5 h-5 animate-spin" />
              ) : (
                <Send className="w-5 h-5 ml-1" />
              )}
            </Button>

            <div className="mt-2 flex justify-between items-center px-2">
               <span className="text-[10px] font-bold text-muted-foreground uppercase tracking-widest">Shift + Enter for new line</span>
               <div className="flex items-center gap-4">
                  <div className="flex items-center gap-1.5">
                     <div className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
                     <span className="text-[10px] font-bold text-emerald-500/80 uppercase tracking-widest leading-none">AI Ready</span>
                  </div>
               </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
