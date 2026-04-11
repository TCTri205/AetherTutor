import { Tag, X } from 'lucide-react';
import { cn } from '../../lib/utils';

interface TagFilterProps {
  tags: string[];
  selectedTag: string | null;
  onTagChange: (tag: string | null) => void;
  entityCounts?: Record<string, number>;
  className?: string;
}

export default function TagFilter({ 
  tags, 
  selectedTag, 
  onTagChange, 
  entityCounts = {},
  className 
}: TagFilterProps) {
  if (tags.length === 0) {
    return null;
  }

  return (
    <div className={cn("space-y-3", className)}>
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Tag className="w-3.5 h-3.5 text-muted-foreground" />
          <h5 className="text-[10px] font-bold text-muted-foreground uppercase tracking-widest">
            Filter by Tag
          </h5>
        </div>
        {selectedTag && (
          <button
            onClick={() => onTagChange(null)}
            className="text-[9px] text-muted-foreground hover:text-white transition-colors flex items-center gap-1"
          >
            Clear
            <X className="w-3 h-3" />
          </button>
        )}
      </div>

      <div className="flex flex-wrap gap-2">
        {tags.map((tag) => {
          const isSelected = selectedTag === tag;
          const count = entityCounts[tag] || 0;
          
          return (
            <button
              key={tag}
              onClick={() => onTagChange(isSelected ? null : tag)}
              className={cn(
                "px-2.5 py-1.5 rounded-lg text-xs font-medium transition-all",
                "border hover:border-primary/50 hover:bg-primary/10",
                isSelected
                  ? "bg-primary/20 border-primary/40 text-primary shadow-sm"
                  : "bg-white/5 border-white/10 text-muted-foreground"
              )}
            >
              <span className="font-bold">#{tag}</span>
              {count > 0 && (
                <span className={cn(
                  "ml-1 text-[9px]",
                  isSelected ? "text-primary/80" : "text-muted-foreground/60"
                )}>
                  {count}
                </span>
              )}
            </button>
          );
        })}
      </div>
    </div>
  );
}
