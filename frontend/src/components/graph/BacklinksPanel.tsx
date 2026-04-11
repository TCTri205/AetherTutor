import { useState, useEffect } from 'react';
import { ArrowRight, Loader2, Link as LinkIcon } from 'lucide-react';
import { graphService } from '../../services/graph';
import { cn } from '../../lib/utils';

interface Backlink {
  id: string;
  source_id: string;
  source_name: string;
  relation_type: string;
  description: string;
  source: string;
}

interface BacklinksPanelProps {
  entityId: string;
  onLinkClick?: (entityName: string) => void;
}

export default function BacklinksPanel({ entityId, onLinkClick }: BacklinksPanelProps) {
  const [backlinks, setBacklinks] = useState<Backlink[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    if (!entityId) return;

    const fetchBacklinks = async () => {
      setIsLoading(true);
      try {
        const data = await graphService.getBacklinks(entityId);
        setBacklinks(data);
      } catch (err) {
        console.error('Failed to fetch backlinks', err);
      } finally {
        setIsLoading(false);
      }
    };

    fetchBacklinks();
  }, [entityId]);

  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center p-8 gap-2">
        <Loader2 className="w-5 h-5 text-primary animate-spin" />
        <span className="text-[10px] text-muted-foreground uppercase tracking-widest font-bold">
          Đang tìm liên kết ngược...
        </span>
      </div>
    );
  }

  if (backlinks.length === 0) {
    return null;
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2 mb-2">
        <LinkIcon className="w-3.5 h-3.5 text-indigo-400" />
        <h5 className="text-[10px] font-bold text-muted-foreground uppercase tracking-widest">
          Incoming Links ({backlinks.length})
        </h5>
      </div>
      <div className="space-y-2">
        {backlinks.map((bl) => (
          <button
            key={bl.id}
            onClick={() => onLinkClick?.(bl.source_name)}
            className={cn(
              "w-full text-left p-3 rounded-xl transition-all",
              "bg-indigo-500/5 border border-indigo-500/10",
              "hover:bg-indigo-500/10 hover:border-indigo-500/30",
              "group"
            )}
          >
            <div className="flex items-center justify-between mb-1">
              <span className="text-xs font-semibold text-white group-hover:text-primary transition-colors">
                {bl.source_name}
              </span>
              <ArrowRight className="w-3 h-3 text-muted-foreground rotate-180 group-hover:text-primary transition-colors" />
            </div>
            <div className="flex items-center gap-2">
              <span className="text-[9px] text-indigo-400 font-bold uppercase tracking-wider px-1.5 py-0.5 rounded bg-indigo-500/10 border border-indigo-500/20">
                {bl.relation_type}
              </span>
              {bl.source === 'obsidian_import' && (
                <span className="text-[8px] bg-purple-500/20 text-purple-300 px-1 rounded uppercase font-bold">
                  Obsidian
                </span>
              )}
            </div>
            {bl.description && (
              <p className="mt-1.5 text-[10px] text-muted-foreground leading-relaxed line-clamp-2 italic">
                "{bl.description}"
              </p>
            )}
          </button>
        ))}
      </div>
    </div>
  );
}
