import '../styles/tokens.css';
import { motion } from 'framer-motion';
import { Share2 } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { cn } from '../../lib/utils';

interface ContextChipsProps {
  entities: string[];
  documentId: string;
  className?: string;
}

/**
 * ContextChips - Hiển thị các entities được tìm thấy trong retrieval context
 * Từ SSE `done` event's `found_entities`
 * Click vào chip → navigate sang Graph và highlight node tương ứng
 */
export default function ContextChips({ entities, documentId, className }: ContextChipsProps) {
  const navigate = useNavigate();

  if (!entities || entities.length === 0) return null;

  const handleEntityClick = (entityName: string) => {
    // Navigate to Graph với highlight entity
    // TODO: Truyền entity name sang Graph page qua state/params
    navigate(`/graph/${documentId}`, {
      state: { highlightEntity: entityName }
    });
  };

  return (
    <div className={cn("flex flex-wrap items-center gap-2 mt-3", className)}>
      <span className="text-[10px] font-bold text-muted-foreground uppercase tracking-widest flex items-center gap-1">
        <Share2 className="w-3 h-3" />
        Entities liên quan
      </span>
      {entities.slice(0, 8).map((entity, index) => (
        <motion.button
          key={entity}
          initial={{ opacity: 0, scale: 0.8 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ delay: index * 0.05 }}
          onClick={() => handleEntityClick(entity)}
          className="px-3 py-1 rounded-full bg-primary/10 border border-primary/20 text-[11px] font-semibold text-primary hover:bg-primary/20 hover:border-primary/40 transition-all cursor-pointer"
        >
          {entity}
        </motion.button>
      ))}
      {entities.length > 8 && (
        <span className="text-[10px] text-muted-foreground font-medium">
          +{entities.length - 8} thêm
        </span>
      )}
    </div>
  );
}
