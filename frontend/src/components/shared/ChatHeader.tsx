import '../styles/tokens.css';
import { Brain, Star, Settings, ChevronLeft, LayoutPanelLeft } from 'lucide-react';
import { Button } from '../ui/Button';
import { Badge } from '../ui/Badge';
import { cn } from '../../lib/utils';
import { Link, useNavigate } from 'react-router-dom';
import { toast } from 'sonner';

interface ChatHeaderProps {
  documentId: string;
  filename: string;
  mode: 'socratic' | 'feynman';
  setMode: (mode: 'socratic' | 'feynman') => void;
}

export default function ChatHeader({ documentId, filename, mode, setMode }: ChatHeaderProps) {
  const navigate = useNavigate();

  return (
    <header className="h-16 border-b border-border-primary flex items-center justify-between px-6 z-10 glass-dark">
      <div className="flex items-center gap-4 flex-1">
        <Button
          variant="ghost"
          size="icon"
          onClick={() => navigate('/vault')}
          className="rounded-xl"
        >
          <ChevronLeft className="w-5 h-5 text-secondary" />
        </Button>
        <div className="w-[1px] h-6 bg-border-primary hidden sm:block" />
        <div className="flex flex-col min-w-0 max-w-sm md:max-w-md">
           <span className="text-[10px] font-bold text-primary tracking-[0.15em] uppercase leading-none">Conversation Context</span>
           <h2 className="text-sm font-bold text-primary truncate">{filename}</h2>
        </div>
      </div>

      {/* S6.10: MVP Scope — Only Feynman active, Socratic disabled */}
      <div className="flex items-center gap-4 bg-secondary p-1 rounded-2xl border border-border-primary">
        <button
          onClick={() => {
            toast.info('Socratic Mode coming soon in v2', { duration: 2000 });
          }}
          disabled
          className="flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-bold transition-all text-secondary/50 cursor-not-allowed relative group"
          title="Coming soon in v2"
        >
          <Brain className="w-4 h-4" />
          Socratic
          {/* Tooltip */}
          <span className="absolute -bottom-8 left-1/2 -translate-x-1/2 px-2 py-1 rounded bg-black text-[10px] text-white whitespace-nowrap opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none">
            Coming soon in v2
          </span>
        </button>
        <button
          onClick={() => setMode('feynman')}
          className={cn(
            "flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-bold transition-all",
            mode === 'feynman'
              ? "bg-amber-500 text-white shadow-lg shadow-amber-500/20"
              : "text-muted-foreground hover:text-white"
          )}
        >
          <Star className="w-4 h-4" />
          Feynman
        </button>
      </div>

      <div className="flex items-center gap-2 ml-4 md:ml-0">
        <Button variant="ghost" size="icon" className="rounded-xl" onClick={() => navigate(`/graph/${documentId}`)}>
           <LayoutPanelLeft className="w-5 h-5 text-secondary hover:text-emerald-500 transition-colors" />
        </Button>
        <Button
          variant="ghost"
          size="icon"
          className="rounded-xl"
          onClick={() => toast.info('Settings page coming soon in v2', { duration: 2000 })}
        >
           <Settings className="w-5 h-5 text-secondary" />
        </Button>
      </div>
    </header>
  );
}
