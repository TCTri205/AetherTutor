import { useState, useEffect, useRef } from 'react';
import { Search, X, ArrowRight } from 'lucide-react';
import { Card } from '../ui/Card';
import { cn } from '../../lib/utils';

interface GraphSearchBarProps {
  nodes: Array<{ id: string; name: string; type?: string; description?: string }>;
  onNodeSelect: (node: any) => void;
  onClose: () => void;
  className?: string;
}

export default function GraphSearchBar({ nodes, onNodeSelect, onClose, className }: GraphSearchBarProps) {
  const [query, setQuery] = useState('');
  const [isOpen, setIsOpen] = useState(false);
  const [selectedIndex, setSelectedIndex] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  const filteredNodes = query.length > 0
    ? nodes.filter(node => 
        node.name.toLowerCase().includes(query.toLowerCase()) ||
        node.description?.toLowerCase().includes(query.toLowerCase())
      )
    : [];

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setSelectedIndex(prev => (prev + 1) % filteredNodes.length);
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setSelectedIndex(prev => (prev - 1 + filteredNodes.length) % filteredNodes.length);
    } else if (e.key === 'Enter' && filteredNodes.length > 0) {
      e.preventDefault();
      handleSelect(filteredNodes[selectedIndex]);
    } else if (e.key === 'Escape') {
      onClose();
    }
  };

  const handleSelect = (node: any) => {
    onNodeSelect(node);
    setQuery('');
    setIsOpen(false);
    onClose();
  };

  const typeColors: Record<string, string> = {
    concept: 'text-indigo-400',
    term: 'text-amber-400',
    process: 'text-emerald-400',
    theory: 'text-purple-400',
    note: 'text-cyan-400',
  };

  return (
    <div className={cn("absolute top-6 right-6 z-10 w-80", className)}>
      <Card className="glass px-4 py-3 border-white/10 shadow-2xl">
        <div className="flex items-center gap-3 mb-2">
          <Search className="w-4 h-4 text-muted-foreground shrink-0" />
          <input
            ref={inputRef}
            type="text"
            value={query}
            onChange={(e) => {
              setQuery(e.target.value);
              setIsOpen(true);
              setSelectedIndex(0);
            }}
            onFocus={() => setIsOpen(true)}
            onKeyDown={handleKeyDown}
            placeholder="Tìm kiếm thực thể..."
            className="flex-1 bg-transparent text-sm text-white placeholder:text-muted-foreground focus:outline-none"
          />
          <button onClick={onClose} className="text-muted-foreground hover:text-white">
            <X className="w-4 h-4" />
          </button>
        </div>

        {isOpen && query.length > 0 && (
          <div className="mt-3 max-h-60 overflow-y-auto border-t border-white/10 pt-2">
            {filteredNodes.length === 0 ? (
              <p className="text-xs text-muted-foreground text-center py-4">
                Không tìm thấy thực thể nào
              </p>
            ) : (
              <div className="space-y-1">
                {filteredNodes.map((node, index) => (
                  <button
                    key={node.id}
                    onClick={() => handleSelect(node)}
                    className={cn(
                      "w-full text-left px-3 py-2 rounded-lg transition-all",
                      "hover:bg-white/5",
                      index === selectedIndex && "bg-white/5 border border-white/10"
                    )}
                  >
                    <div className="flex items-center justify-between">
                      <span className="text-sm font-medium text-white truncate flex-1">
                        {node.name}
                      </span>
                      <ArrowRight className="w-3 h-3 text-muted-foreground ml-2 shrink-0" />
                    </div>
                    <div className="flex items-center gap-2 mt-1">
                      <span className={cn(
                        "text-[9px] font-bold uppercase tracking-wider",
                        typeColors[node.type?.toLowerCase() || ''] || 'text-slate-400'
                      )}>
                        {node.type || 'unknown'}
                      </span>
                      {node.description && (
                        <span className="text-[9px] text-muted-foreground/60 truncate ml-1">
                          {node.description.slice(0, 50)}...
                        </span>
                      )}
                    </div>
                  </button>
                ))}
              </div>
            )}
          </div>
        )}
      </Card>
    </div>
  );
}
