/**
 * MathChat — Chat UI cho Math Tutoring Agent với KaTeX rendering.
 *
 * Features:
 * - Chat interface với math-specific responses
 * - LaTeX rendering (inline $...$ và display $$...$$)
 * - Step-by-step solutions
 * - Formula extraction
 * - Topic & level selector
 * - Practice mode
 */
import { useState, useRef, useEffect } from 'react';
import { Send, Calculator, Sparkles, ChevronDown, ChevronUp } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { toast } from 'sonner';

// Simple LaTeX renderer (in production, use katex library)
function LaTeXRenderer({ content }: { content: string }) {
  // Replace $formula$ with styled spans
  const parts = content.split(/(\$[^$]+\$|\$\$[\s\S]*?\$\$)/g);

  return (
    <span>
      {parts.map((part, i) => {
        if (part.startsWith('$$') && part.endsWith('$$')) {
          // Display math
          const formula = part.slice(2, -2);
          return (
            <div key={i} className="my-3 p-3 rounded bg-bg-tertiary border border-border-primary text-center font-mono text-lg text-accent">
              {formula}
            </div>
          );
        } else if (part.startsWith('$') && part.endsWith('$')) {
          // Inline math
          const formula = part.slice(1, -1);
          return (
            <span key={i} className="inline-block px-1 py-0.5 mx-0.5 rounded bg-bg-tertiary font-mono text-sm text-accent">
              {formula}
            </span>
          );
        }
        return <span key={i}>{part}</span>;
      })}
    </span>
  );
}

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  steps?: Step[];
  formulas?: string[];
}

interface Step {
  number: number;
  description: string;
  formula?: string;
}

const TOPICS = [
  { id: 'algebra', label: '🔢 Algebra' },
  { id: 'geometry', label: '📐 Geometry' },
  { id: 'calculus', label: '∫ Calculus' },
  { id: 'statistics', label: '📊 Statistics' },
  { id: 'probability', label: '🎲 Probability' },
  { id: 'linear_algebra', label: '🔲 Linear Algebra' },
  { id: 'discrete_math', label: '🔗 Discrete Math' },
  { id: 'number_theory', label: '#️⃣ Number Theory' },
  { id: 'trigonometry', label: '📏 Trigonometry' },
];

const LEVELS = [
  { id: 'elementary', label: '🌱 Tiểu học' },
  { id: 'middle_school', label: '📚 Cấp 2' },
  { id: 'high_school', label: '🎓 Cấp 3' },
  { id: 'undergraduate', label: '🎓 Đại học' },
  { id: 'graduate', label: '🔬 Sau đại học' },
];

const TASK_TYPES = [
  { id: 'solve', label: '🧮 Giải bài tập' },
  { id: 'explain', label: '💡 Giải thích' },
  { id: 'practice', label: '💪 Luyện tập' },
  { id: 'extract_formulas', label: '📜 Công thức' },
];

export default function MathChat() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [topic, setTopic] = useState('algebra');
  const [level, setLevel] = useState('high_school');
  const [taskType, setTaskType] = useState('solve');
  const [isLoading, setIsLoading] = useState(false);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);
  const token = localStorage.getItem('token') || '';

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight });
  }, [messages]);

  const handleSend = async () => {
    if (!input.trim() || isLoading) return;

    const userMsg: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: input,
      timestamp: new Date(),
    };
    setMessages(prev => [...prev, userMsg]);
    setInput('');
    setIsLoading(true);

    try {
      const res = await fetch('/api/v1/agents/math_agent/execute', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          task: taskType,
          topic,
          level,
          problem: input,
        }),
      });

      if (!res.ok) throw new Error('Failed to execute agent');

      const data = await res.json();
      const result = data.result || {};

      const assistantMsg: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: result.response || result.explanation || 'Xin lỗi, tôi chưa hiểu bài toán này.',
        timestamp: new Date(),
        steps: result.steps || [],
        formulas: result.formulas || [],
      };
      setMessages(prev => [...prev, assistantMsg]);
    } catch (err: any) {
      toast.error(err.message || 'Lỗi khi gửi tin nhắn');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="p-4 border-b border-border-primary bg-bg-elevated">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <Calculator className="w-5 h-5 text-accent" />
            <h2 className="font-semibold text-text-primary">Math Tutor</h2>
          </div>
          <button
            className="text-sm text-accent hover:underline flex items-center gap-1"
            onClick={() => setShowAdvanced(!showAdvanced)}
          >
            {showAdvanced ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
            Tùy chọn
          </button>
        </div>

        {/* Task type tabs */}
        <div className="flex gap-2 mb-2">
          {TASK_TYPES.map(task => (
            <button
              key={task.id}
              className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                taskType === task.id
                  ? 'bg-accent/20 text-accent'
                  : 'bg-bg-secondary text-text-secondary hover:text-text-primary'
              }`}
              onClick={() => setTaskType(task.id)}
            >
              {task.label}
            </button>
          ))}
        </div>

        {/* Advanced options */}
        <AnimatePresence>
          {showAdvanced && (
            <motion.div
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: 'auto', opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              className="overflow-hidden"
            >
              <div className="flex gap-3 pt-2">
                <div className="flex-1">
                  <label className="block text-xs text-text-secondary mb-1">Chủ đề</label>
                  <select
                    className="w-full px-2 py-1.5 rounded bg-bg-secondary border border-border-primary text-text-primary text-sm"
                    value={topic}
                    onChange={(e) => setTopic(e.target.value)}
                  >
                    {TOPICS.map(t => (
                      <option key={t.id} value={t.id}>{t.label}</option>
                    ))}
                  </select>
                </div>
                <div className="flex-1">
                  <label className="block text-xs text-text-secondary mb-1">Cấp độ</label>
                  <select
                    className="w-full px-2 py-1.5 rounded bg-bg-secondary border border-border-primary text-text-primary text-sm"
                    value={level}
                    onChange={(e) => setLevel(e.target.value)}
                  >
                    {LEVELS.map(l => (
                      <option key={l.id} value={l.id}>{l.label}</option>
                    ))}
                  </select>
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* Messages */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 && (
          <div className="text-center py-12 text-text-secondary">
            <Calculator className="w-12 h-12 mx-auto mb-4 opacity-50" />
            <p className="text-lg font-medium">Bắt đầu học toán</p>
            <p className="text-sm mt-1">
              Nhập bài toán hoặc câu hỏi, AI sẽ giải step-by-step
            </p>
          </div>
        )}

        <AnimatePresence>
          {messages.map(msg => (
            <motion.div
              key={msg.id}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              <div
                className={`max-w-[80%] rounded-lg p-3 ${
                  msg.role === 'user'
                    ? 'bg-accent text-white'
                    : 'bg-bg-elevated border border-border-primary text-text-primary'
                }`}
              >
                <LaTeXRenderer content={msg.content} />

                {/* Step-by-step solutions */}
                {msg.steps && msg.steps.length > 0 && (
                  <div className="mt-3 space-y-2">
                    <p className="text-xs font-semibold text-accent uppercase">Step-by-Step Solution</p>
                    {msg.steps.map((step, i) => (
                      <div
                        key={i}
                        className="p-3 rounded bg-bg-secondary border border-border-primary"
                      >
                        <div className="flex items-start gap-2">
                          <span className="flex-shrink-0 w-6 h-6 rounded-full bg-accent/20 text-accent text-xs font-bold flex items-center justify-center">
                            {step.number}
                          </span>
                          <div>
                            <p className="text-sm text-text-primary">{step.description}</p>
                            {step.formula && (
                              <div className="mt-1 p-2 rounded bg-bg-tertiary font-mono text-sm text-accent text-center">
                                {step.formula}
                              </div>
                            )}
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                )}

                {/* Formulas */}
                {msg.formulas && msg.formulas.length > 0 && (
                  <div className="mt-3">
                    <p className="text-xs font-semibold text-accent uppercase">Formulas Used</p>
                    <div className="flex flex-wrap gap-2 mt-2">
                      {msg.formulas.map((f, i) => (
                        <span
                          key={i}
                          className="px-2 py-1 rounded bg-bg-tertiary font-mono text-sm text-accent border border-border-primary"
                        >
                          {f}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </motion.div>
          ))}
        </AnimatePresence>

        {isLoading && (
          <div className="flex justify-start">
            <div className="bg-bg-elevated border border-border-primary rounded-lg p-3">
              <div className="flex items-center gap-2 text-text-secondary">
                <Sparkles className="w-4 h-4 animate-pulse" />
                <span className="text-sm">Đang giải toán...</span>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Input */}
      <div className="p-4 border-t border-border-primary bg-bg-elevated">
        <div className="flex gap-2">
          <input
            type="text"
            className="flex-1 px-3 py-2 rounded-lg bg-bg-secondary border border-border-primary text-text-primary placeholder:text-text-secondary focus:outline-none focus:ring-2 focus:ring-accent/50"
            placeholder="Nhập bài toán hoặc công thức (dùng $...$ cho LaTeX)..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && !e.shiftKey && handleSend()}
            disabled={isLoading}
          />
          <button
            className="px-4 py-2 bg-accent text-white rounded-lg hover:bg-accent/90 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
            onClick={handleSend}
            disabled={isLoading || !input.trim()}
          >
            <Send className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  );
}
