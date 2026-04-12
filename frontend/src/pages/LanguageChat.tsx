/**
 * LanguageChat — Chat UI cho Language Learning Agent.
 *
 * Features:
 * - Chat interface với language-specific responses
 * - Vocabulary cards (word, definition, example, POS)
 * - Grammar highlights
 * - Conjugation tables
 * - Translation exercises
 * - Language selector
 */
import { useState, useRef, useEffect } from 'react';
import { Send, BookOpen, Languages, Sparkles } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { toast } from 'sonner';

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  vocabCards?: VocabCard[];
  grammarNotes?: GrammarNote[];
}

interface VocabCard {
  word: string;
  definition: string;
  example: string;
  pos: string; // part of speech
  frequency: 'common' | 'uncommon' | 'rare';
}

interface GrammarNote {
  pattern: string;
  description: string;
  examples: string[];
}

const SUPPORTED_LANGUAGES = [
  { code: 'en', name: 'English', flag: '🇬🇧' },
  { code: 'vi', name: 'Vietnamese', flag: '🇻🇳' },
  { code: 'fr', name: 'French', flag: '🇫🇷' },
  { code: 'es', name: 'Spanish', flag: '🇪🇸' },
  { code: 'de', name: 'German', flag: '🇩🇪' },
  { code: 'zh', name: 'Chinese', flag: '🇨🇳' },
  { code: 'ja', name: 'Japanese', flag: '🇯🇵' },
  { code: 'ko', name: 'Korean', flag: '🇰🇷' },
];

const TASK_TYPES = [
  { id: 'vocabulary', label: '📚 Vocabulary', icon: '📚' },
  { id: 'grammar', label: '📝 Grammar', icon: '📝' },
  { id: 'translation', label: '🌐 Translation', icon: '🌐' },
  { id: 'exercise', label: '💪 Exercise', icon: '💪' },
];

export default function LanguageChat() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [selectedLang, setSelectedLang] = useState('en');
  const [taskType, setTaskType] = useState('vocabulary');
  const [isLoading, setIsLoading] = useState(false);
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
      const res = await fetch('/api/v1/agents/language_agent/execute', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          task: taskType,
          language: selectedLang,
          input_text: input,
        }),
      });

      if (!res.ok) throw new Error('Failed to execute agent');

      const data = await res.json();
      const result = data.result || {};

      const assistantMsg: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: result.response || result.explanation || 'Xin lỗi, tôi chưa hiểu yêu cầu này.',
        timestamp: new Date(),
        vocabCards: result.vocab_cards || [],
        grammarNotes: result.grammar_patterns || [],
      };
      setMessages(prev => [...prev, assistantMsg]);
    } catch (err: any) {
      toast.error(err.message || 'Lỗi khi gửi tin nhắn');
    } finally {
      setIsLoading(false);
    }
  };

  const currentLang = SUPPORTED_LANGUAGES.find(l => l.code === selectedLang);

  return (
    <div className="flex flex-col h-full">
      {/* Header với language selector */}
      <div className="p-4 border-b border-border-primary bg-bg-elevated">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <Languages className="w-5 h-5 text-accent" />
            <h2 className="font-semibold text-text-primary">Language Learning</h2>
          </div>
          <select
            className="px-3 py-1.5 rounded-lg bg-bg-secondary border border-border-primary text-text-primary text-sm"
            value={selectedLang}
            onChange={(e) => setSelectedLang(e.target.value)}
          >
            {SUPPORTED_LANGUAGES.map(lang => (
              <option key={lang.code} value={lang.code}>
                {lang.flag} {lang.name}
              </option>
            ))}
          </select>
        </div>

        {/* Task type tabs */}
        <div className="flex gap-2">
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
      </div>

      {/* Messages */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 && (
          <div className="text-center py-12 text-text-secondary">
            <BookOpen className="w-12 h-12 mx-auto mb-4 opacity-50" />
            <p className="text-lg font-medium">Bắt đầu học ngôn ngữ</p>
            <p className="text-sm mt-1">
              Chọn ngôn ngữ và loại task, sau đó gửi tin nhắn
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
                <p className="whitespace-pre-wrap">{msg.content}</p>

                {/* Vocabulary Cards */}
                {msg.vocabCards && msg.vocabCards.length > 0 && (
                  <div className="mt-3 space-y-2">
                    <p className="text-xs font-semibold text-accent uppercase">Vocabulary</p>
                    {msg.vocabCards.map((card, i) => (
                      <div
                        key={i}
                        className="p-3 rounded bg-bg-secondary border border-border-primary"
                      >
                        <div className="flex items-center justify-between">
                          <span className="font-semibold text-text-primary">{card.word}</span>
                          <span className="text-xs px-2 py-0.5 rounded bg-accent/10 text-accent">
                            {card.pos}
                          </span>
                        </div>
                        <p className="text-sm text-text-secondary mt-1">{card.definition}</p>
                        <p className="text-xs text-text-secondary mt-1 italic">
                          "{card.example}"
                        </p>
                        <span
                          className={`inline-block mt-1 text-xs px-1.5 py-0.5 rounded ${
                            card.frequency === 'common'
                              ? 'bg-green-500/20 text-green-400'
                              : card.frequency === 'uncommon'
                              ? 'bg-yellow-500/20 text-yellow-400'
                              : 'bg-red-500/20 text-red-400'
                          }`}
                        >
                          {card.frequency}
                        </span>
                      </div>
                    ))}
                  </div>
                )}

                {/* Grammar Notes */}
                {msg.grammarNotes && msg.grammarNotes.length > 0 && (
                  <div className="mt-3 space-y-2">
                    <p className="text-xs font-semibold text-accent uppercase">Grammar</p>
                    {msg.grammarNotes.map((note, i) => (
                      <div
                        key={i}
                        className="p-3 rounded bg-bg-secondary border border-border-primary"
                      >
                        <p className="font-mono text-sm text-accent">{note.pattern}</p>
                        <p className="text-sm text-text-secondary mt-1">{note.description}</p>
                        {note.examples.map((ex, j) => (
                          <p key={j} className="text-xs text-text-secondary mt-0.5 italic">
                            → {ex}
                          </p>
                        ))}
                      </div>
                    ))}
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
                <span className="text-sm">Đang phân tích...</span>
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
            placeholder={`Nhập câu hỏi hoặc đoạn văn bằng ${currentLang?.name}...`}
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
