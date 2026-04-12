import { useEffect, useRef, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, Keyboard } from 'lucide-react';

type ShortcutCategory = 'Navigation' | 'Actions' | 'Help';

interface ShortcutItem {
  keys: string[];
  description: string;
  category: ShortcutCategory;
}

const SHORTCUTS: ShortcutItem[] = [
  // Navigation
  { keys: ['Ctrl', 'K'], description: 'Open command palette', category: 'Navigation' },
  { keys: ['Ctrl', 'N'], description: 'New chat', category: 'Navigation' },
  { keys: ['Ctrl', 'Tab'], description: 'Switch to next tab', category: 'Navigation' },

  // Actions
  { keys: ['Ctrl', 'Enter'], description: 'Send message', category: 'Actions' },
  { keys: ['Ctrl', 'Shift', 'F'], description: 'Search flashcards', category: 'Actions' },
  { keys: ['Ctrl', 'U'], description: 'Open upload dialog', category: 'Actions' },

  // Help
  { keys: ['Ctrl', '/'], description: 'Open this shortcuts modal', category: 'Help' },
  { keys: ['?'], description: 'Toggle shortcuts (when not typing)', category: 'Help' },
];

const isMac = typeof navigator !== 'undefined' && /Mac|iPod|iPhone|iPad/.test(navigator.platform);

function formatKey(key: string): string {
  if (isMac) {
    const macMap: Record<string, string> = {
      'Ctrl': '\u2318',
      'Alt': '\u2325',
      'Shift': '\u21E7',
    };
    return macMap[key] || key;
  }
  return key;
}

interface KeyboardShortcutsModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export default function KeyboardShortcutsModal({ open, onOpenChange }: KeyboardShortcutsModalProps) {
  const modalRef = useRef<HTMLDivElement>(null);

  const handleClose = useCallback(() => onOpenChange(false), [onOpenChange]);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        handleClose();
        return;
      }
      if ((e.ctrlKey || e.metaKey) && e.key === '/') {
        e.preventDefault();
        onOpenChange(!open);
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [open, onOpenChange, handleClose]);

  const categories: ShortcutCategory[] = ['Navigation', 'Actions', 'Help'];

  return (
    <AnimatePresence>
      {open && (
        <motion.div
          role="dialog"
          aria-modal="true"
          aria-label="Keyboard Shortcuts"
          className="fixed inset-0 z-50 flex items-center justify-center"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          onClick={(e) => { if (e.target === e.currentTarget) handleClose(); }}
        >
          <div className="absolute inset-0 bg-[var(--bg-overlay)] backdrop-blur-sm" />
          <motion.div
            ref={modalRef}
            className="relative w-full max-w-lg mx-4 rounded-2xl border border-[var(--border-glass)] bg-[var(--bg-elevated)] shadow-[var(--shadow-xl)] overflow-hidden"
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.95 }}
            transition={{ duration: 0.2, ease: 'easeOut' }}
          >
            <div className="flex items-center justify-between px-6 py-4 border-b border-[var(--border-primary)]">
              <div className="flex items-center gap-2">
                <Keyboard className="w-5 h-5 text-[var(--accent-primary)]" />
                <h2 className="text-lg font-semibold text-[var(--text-primary)]">Keyboard Shortcuts</h2>
              </div>
              <button
                onClick={handleClose}
                aria-label="Close"
                className="p-1.5 rounded-lg text-[var(--text-tertiary)] hover:text-[var(--text-primary)] hover:bg-[var(--accent-primary-muted)] transition-colors"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="px-6 py-4 max-h-[60vh] overflow-y-auto">
              {categories.map((category) => {
                const items = SHORTCUTS.filter((s) => s.category === category);
                if (items.length === 0) return null;

                return (
                  <div key={category} className="mb-4 last:mb-0">
                    <h3 className="text-xs font-medium uppercase tracking-wider text-[var(--text-tertiary)] mb-2">
                      {category}
                    </h3>
                    <div className="space-y-2">
                      {items.map((shortcut, idx) => (
                        <div
                          key={idx}
                          className="flex items-center justify-between py-2"
                        >
                          <span className="text-sm text-[var(--text-secondary)]">{shortcut.description}</span>
                          <div className="flex items-center gap-1">
                            {shortcut.keys.map((key) => (
                              <kbd
                                key={key}
                                className="px-2 py-1 text-xs font-mono rounded-md border border-[var(--border-primary)] bg-[var(--bg-secondary)] text-[var(--text-primary)] shadow-sm"
                              >
                                {formatKey(key)}
                              </kbd>
                            ))}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                );
              })}
            </div>

            <div className="px-6 py-3 border-t border-[var(--border-primary)] bg-[var(--bg-secondary)]">
              <p className="text-xs text-[var(--text-tertiary)] text-center">
                Press <kbd className="px-1.5 py-0.5 font-mono rounded border border-[var(--border-primary)] bg-[var(--bg-elevated)]">Esc</kbd> to close
              </p>
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
