import { motion, AnimatePresence } from 'framer-motion';
import {
  X,
  Zap,
  Share2,
  MessageSquare,
  ArrowRight,
  Hash
} from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { Button } from '../ui/Button';
import { Badge } from '../ui/Badge';
import { cn } from '../../lib/utils';

interface GraphSidebarProps {
  isOpen: boolean;
  onClose: () => void;
  entity: GraphEntityData | null;
  documentId: string;
}

interface GraphEntityData {
  id: string;
  label: string;
  type: string;
  description?: string;
  neighbors?: Array<{
    target: string;
    relation_type: string;
    description?: string;
  }>;
  degree?: number;
}

const typeColors: Record<string, string> = {
  concept: 'bg-indigo-500/20 text-indigo-400 border-indigo-500/30',
  term: 'bg-amber-500/20 text-amber-400 border-amber-500/30',
  process: 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30',
  theory: 'bg-purple-500/20 text-purple-400 border-purple-500/30',
};

const typeIcons: Record<string, any> = {
  concept: Zap,
  term: Hash,
  process: Share2,
  theory: MessageSquare,
};

export default function GraphSidebar({ isOpen, onClose, entity, documentId }: GraphSidebarProps) {
  const navigate = useNavigate();

  if (!entity) return null;

  const TypeIcon = typeIcons[entity.type?.toLowerCase()] || Zap;
  const typeColor = typeColors[entity.type?.toLowerCase()] || typeColors.concept;

  const handleChatAboutEntity = () => {
    // Navigate to chat with pre-filled query about this entity
    navigate(`/chat/${documentId}`, {
      state: { prefillQuery: `Giải thích về "${entity.label}"` }
    });
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <motion.div
          initial={{ width: 0, opacity: 0 }}
          animate={{ width: 320, opacity: 1 }}
          exit={{ width: 0, opacity: 0 }}
          transition={{ duration: 0.3, ease: 'easeInOut' }}
          className="border-l border-white/5 bg-black/40 backdrop-blur-xl flex flex-col shrink-0 overflow-hidden"
        >
          {/* Header */}
          <div className="flex items-center justify-between px-4 py-3 border-b border-white/5">
            <h3 className="text-xs font-bold text-muted-foreground uppercase tracking-widest">
              Chi tiết Entity
            </h3>
            <button
              onClick={onClose}
              className="p-1.5 rounded-lg hover:bg-white/10 transition-colors"
            >
              <X className="w-4 h-4 text-muted-foreground" />
            </button>
          </div>

          {/* Content */}
          <div className="flex-1 overflow-y-auto p-4 space-y-4">
            {/* Entity Header */}
            <div className="flex items-start gap-3">
              <div className={cn(
                "w-10 h-10 rounded-xl flex items-center justify-center border",
                typeColor
              )}>
                <TypeIcon className="w-5 h-5" />
              </div>
              <div className="flex-1 min-w-0">
                <h4 className="text-sm font-bold text-white truncate">
                  {entity.label}
                </h4>
                <Badge variant="outline" className="mt-1 text-[10px] uppercase tracking-wider">
                  {entity.type || 'Entity'}
                </Badge>
              </div>
            </div>

            {/* Description */}
            {entity.description && (
              <div className="p-3 rounded-xl bg-white/5 border border-white/10">
                <p className="text-xs text-muted-foreground leading-relaxed">
                  {entity.description}
                </p>
              </div>
            )}

            {/* Stats */}
            <div className="grid grid-cols-2 gap-2">
              <div className="p-3 rounded-xl bg-white/5 border border-white/10">
                <p className="text-[10px] text-muted-foreground uppercase tracking-wider mb-1">
                  Bậc liên kết
                </p>
                <p className="text-lg font-bold text-white">
                  {entity.degree || entity.neighbors?.length || 0}
                </p>
              </div>
              <div className="p-3 rounded-xl bg-white/5 border border-white/10">
                <p className="text-[10px] text-muted-foreground uppercase tracking-wider mb-1">
                  Loại
                </p>
                <p className="text-sm font-bold text-primary capitalize">
                  {entity.type || 'concept'}
                </p>
              </div>
            </div>

            {/* Neighbors / Relationships */}
            {entity.neighbors && entity.neighbors.length > 0 && (
              <div>
                <h5 className="text-[10px] font-bold text-muted-foreground uppercase tracking-widest mb-2">
                  Quan hệ ({entity.neighbors.length})
                </h5>
                <div className="space-y-2">
                  {entity.neighbors.map((neighbor, idx) => (
                    <div
                      key={idx}
                      className="p-3 rounded-xl bg-white/5 border border-white/10 hover:border-primary/30 transition-colors"
                    >
                      <div className="flex items-center gap-2 mb-1">
                        <ArrowRight className="w-3 h-3 text-primary" />
                        <span className="text-xs font-semibold text-white">
                          {neighbor.target}
                        </span>
                      </div>
                      <p className="text-[10px] text-primary font-bold uppercase tracking-wider mb-1">
                        {neighbor.relation_type}
                      </p>
                      {neighbor.description && (
                        <p className="text-[10px] text-muted-foreground leading-relaxed">
                          {neighbor.description}
                        </p>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Chat about entity button */}
            <Button
              variant="default"
              className="w-full gap-2"
              onClick={handleChatAboutEntity}
            >
              <MessageSquare className="w-4 h-4" />
              Chat về entity này
            </Button>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
