import '../styles/tokens.css';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import remarkMath from 'remark-math';
import rehypeKatex from 'rehype-katex';
import { User, Bot, Sparkles, ChevronDown, ChevronUp } from 'lucide-react';
import { cn } from '../../lib/utils';
import { useState, memo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import MermaidDiagram from './MermaidDiagram';

interface ChatMessageProps {
  role: 'user' | 'assistant';
  content: string;
  reasoning?: string;
  isStreaming?: boolean;
}

// Memoize to prevent re-rendering entire message list on every streaming chunk
const ChatMessage = memo(function ChatMessage({ role, content, reasoning, isStreaming }: ChatMessageProps) {
  const [showReasoning, setShowReasoning] = useState(true);
  const isUser = role === 'user';

  return (
    <div className={cn(
      "flex w-full gap-4 py-8 px-4 md:px-0 group transition-colors",
      isUser ? "bg-transparent" : "bg-secondary"
    )}>
      <div className="max-w-4xl mx-auto flex w-full gap-4 md:gap-6">
        {/* Avatar */}
        <div className={cn(
          "w-10 h-10 rounded-2xl flex items-center justify-center shrink-0 shadow-lg",
          isUser 
            ? "bg-secondary text-secondary-foreground" 
            : "bg-gradient-to-tr from-primary to-blue-400 text-white shadow-primary/20"
        )}>
          {isUser ? <User className="w-5 h-5" /> : <Bot className="w-6 h-6" />}
        </div>

        {/* Content Area */}
        <div className="flex-1 space-y-4 overflow-hidden">
          <div className="flex items-center gap-2">
            <span className="font-bold text-sm tracking-tight text-primary">
              {isUser ? 'Bạn' : 'Aether Tutor'}
            </span>
            {!isUser && (
              <div className="flex items-center gap-1 px-2 py-0.5 rounded-full bg-primary/10 border border-primary/20 text-[10px] font-bold text-primary uppercase tracking-widest">
                <Sparkles className="w-3 h-3 fill-primary" />
                Socratic
              </div>
            )}
          </div>

          {/* Reasoning / Thinking Process */}
          <AnimatePresence>
            {!isUser && reasoning && (
              <motion.div 
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: 'auto' }}
                className="border-l-2 border-primary/20 pl-4 py-1 my-4"
              >
                <button 
                  onClick={() => setShowReasoning(!showReasoning)}
                  className="flex items-center gap-2 text-[11px] font-bold text-muted-foreground uppercase tracking-[0.2em] hover:text-primary transition-colors py-1"
                >
                  {showReasoning ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
                  Tiến trình suy luận
                </button>
                {showReasoning && (
                  <motion.div 
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    className="text-sm text-muted-foreground italic leading-relaxed mt-2 line-clamp-10"
                  >
                    {reasoning}
                    {isStreaming && !content && <span className="inline-block w-1 h-4 bg-primary ml-1 animate-pulse" />}
                  </motion.div>
                )}
              </motion.div>
            )}
          </AnimatePresence>

          {/* Message Content (Markdown) */}
          <div className={cn(
            "prose prose-invert max-w-none prose-p:leading-relaxed prose-pre:bg-secondary prose-pre:border prose-pre:border-border-primary prose-pre:rounded-2xl prose-code:text-primary prose-headings:text-primary",
            isUser ? "text-secondary" : "text-primary"
          )}>
            <ReactMarkdown
              remarkPlugins={[remarkGfm, remarkMath]}
              rehypePlugins={[rehypeKatex]}
              components={{
                p: ({ children }) => <p className="mb-4 last:mb-0">{children}</p>,
                code: ({ node, inline, className, children, ...props }: any) => {
                  const match = /language-(\w+)/.exec(className || '');
                  const language = match ? match[1] : '';

                  // Detect mermaid code blocks
                  if (language === 'mermaid' && !inline) {
                    const mermaidCode = String(children).replace(/\n$/, '');
                    return <MermaidDiagram code={mermaidCode} />;
                  }

                  return (
                    <code className={cn(className, inline ? "bg-secondary px-1.5 py-0.5 rounded text-primary" : "")} {...props}>
                      {children}
                    </code>
                  )
                }
              }}
            >
              {content}
            </ReactMarkdown>
            {isStreaming && content && (
              <span className="inline-block w-2 h-5 bg-primary ml-1 translate-y-1 animate-pulse rounded-sm" />
            )}
          </div>
        </div>
      </div>
    </div>
  );
});

export default ChatMessage;
