import { motion } from 'framer-motion';
import { cn } from '../../lib/utils';

// ─── Generic Skeleton Primitives ───────────────────────────────────────────────

interface SkeletonBaseProps {
  className?: string;
  'aria-label'?: string;
}

export function SkeletonCircle({ className, ...props }: SkeletonBaseProps) {
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className={cn(
        'rounded-full bg-bg-tertiary animate-pulse',
        'before:absolute before:inset-0 before:rounded-full',
        'before:bg-gradient-to-r before:from-transparent before:via-white/5 before:to-transparent',
        'before:animate-[shimmer_2s_ease-in-out_infinite]',
        'relative overflow-hidden',
        className
      )}
      role="status"
      aria-label="Loading"
      {...props}
    />
  );
}

export function SkeletonBox({ className, ...props }: SkeletonBaseProps) {
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className={cn(
        'rounded-lg bg-bg-tertiary animate-pulse relative overflow-hidden',
        'before:absolute before:inset-0',
        'before:bg-gradient-to-r before:from-transparent before:via-white/5 before:to-transparent',
        'before:animate-[shimmer_2s_ease-in-out_infinite]',
        className
      )}
      role="status"
      aria-label="Loading"
      {...props}
    />
  );
}

export function SkeletonLine({ className, ...props }: SkeletonBaseProps & { className?: string }) {
  return <SkeletonBox className={cn('h-4 w-full', className)} {...props} />;
}

// ─── Dashboard Skeleton ────────────────────────────────────────────────────────

export function DashboardSkeleton() {
  const cardCount = 4;
  return (
    <div className="space-y-6 p-6" role="status" aria-label="Loading dashboard">
      {/* Stats cards grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {Array.from({ length: cardCount }).map((_, i) => (
          <SkeletonBox key={i} className="h-28 p-4 space-y-3">
            <SkeletonCircle className="w-8 h-8" />
            <SkeletonLine className="h-3 w-2/3" />
            <SkeletonLine className="h-5 w-1/2" />
          </SkeletonBox>
        ))}
      </div>
      {/* Recent activity section */}
      <SkeletonBox className="h-64 p-4 space-y-4">
        <SkeletonLine className="h-6 w-1/4" />
        {Array.from({ length: 3 }).map((_, i) => (
          <div key={i} className="flex items-center gap-3">
            <SkeletonCircle className="w-10 h-10" />
            <div className="flex-1 space-y-2">
              <SkeletonLine className="h-4 w-3/4" />
              <SkeletonLine className="h-3 w-1/2" />
            </div>
          </div>
        ))}
      </SkeletonBox>
    </div>
  );
}

// ─── Vault (File List) Skeleton ────────────────────────────────────────────────

export function VaultSkeleton({ count = 6 }: { count?: number }) {
  return (
    <div className="space-y-3 p-4" role="status" aria-label="Loading vault">
      {/* Header placeholder */}
      <div className="flex items-center justify-between mb-4">
        <SkeletonLine className="h-7 w-32" />
        <SkeletonBox className="h-9 w-24" />
      </div>
      {/* File list items */}
      {Array.from({ length: count }).map((_, i) => (
        <div
          key={i}
          className="flex items-center gap-3 p-3 rounded-xl bg-bg-tertiary/50 border border-border-primary/50"
        >
          <SkeletonCircle className="w-10 h-10" />
          <div className="flex-1 space-y-2">
            <SkeletonLine className="h-4 w-2/3" />
            <SkeletonLine className="h-3 w-1/3" />
          </div>
          <SkeletonBox className="h-6 w-16" />
        </div>
      ))}
    </div>
  );
}

// ─── Chat Skeleton ─────────────────────────────────────────────────────────────

export function ChatSkeleton() {
  return (
    <div className="flex flex-col h-full" role="status" aria-label="Loading chat">
      {/* Messages area */}
      <div className="flex-1 overflow-y-auto space-y-6 p-6">
        {/* User message placeholder */}
        <div className="flex gap-3 justify-end">
          <SkeletonBox className="h-12 w-64 rounded-2xl rounded-tr-sm" />
          <SkeletonCircle className="w-9 h-9" />
        </div>
        {/* Assistant message placeholder */}
        <div className="flex gap-3">
          <SkeletonCircle className="w-9 h-9 bg-accent-primary-muted" />
          <div className="space-y-2 flex-1 max-w-lg">
            <SkeletonLine className="h-4 w-full" />
            <SkeletonLine className="h-4 w-5/6" />
            <SkeletonLine className="h-4 w-2/3" />
          </div>
        </div>
        {/* Another user message */}
        <div className="flex gap-3 justify-end">
          <SkeletonBox className="h-10 w-48 rounded-2xl rounded-tr-sm" />
          <SkeletonCircle className="w-9 h-9" />
        </div>
        {/* Another assistant message */}
        <div className="flex gap-3">
          <SkeletonCircle className="w-9 h-9 bg-accent-primary-muted" />
          <div className="space-y-2 flex-1 max-w-md">
            <SkeletonLine className="h-4 w-full" />
            <SkeletonLine className="h-4 w-4/5" />
          </div>
        </div>
      </div>
      {/* Typing indicator */}
      <div className="flex items-center gap-3 px-6 py-3 border-t border-border-primary/50">
        <SkeletonCircle className="w-7 h-7" />
        <div className="flex gap-1.5">
          {[0, 1, 2].map((i) => (
            <motion.div
              key={i}
              className="w-2 h-2 rounded-full bg-bg-tertiary"
              animate={{ y: [0, -4, 0] }}
              transition={{ duration: 0.6, repeat: Infinity, delay: i * 0.15 }}
            />
          ))}
        </div>
        <span className="text-xs text-text-tertiary ml-1">Đang suy nghĩ...</span>
      </div>
      {/* Input bar placeholder */}
      <div className="p-4 border-t border-border-primary/50">
        <SkeletonBox className="h-12 w-full rounded-xl" />
      </div>
    </div>
  );
}

// ─── Flashcards Skeleton ───────────────────────────────────────────────────────

export function FlashcardsSkeleton({ count = 4 }: { count?: number }) {
  return (
    <div className="space-y-6 p-6" role="status" aria-label="Loading flashcards">
      {/* Header */}
      <div className="flex items-center justify-between">
        <SkeletonLine className="h-7 w-40" />
        <div className="flex gap-2">
          <SkeletonBox className="h-9 w-20" />
          <SkeletonBox className="h-9 w-24" />
        </div>
      </div>
      {/* Card stack */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {Array.from({ length: count }).map((_, i) => (
          <SkeletonBox key={i} className="h-48 p-5 space-y-4 flex flex-col justify-between">
            <div className="space-y-3">
              <SkeletonLine className="h-4 w-1/3" />
              <SkeletonLine className="h-5 w-full" />
              <SkeletonLine className="h-5 w-4/5" />
            </div>
            <div className="flex items-center justify-between">
              <SkeletonBox className="h-6 w-16" />
              <SkeletonCircle className="w-6 h-6" />
            </div>
          </SkeletonBox>
        ))}
      </div>
    </div>
  );
}

// ─── Shimmer keyframe injection (runs once) ────────────────────────────────────

if (typeof document !== 'undefined' && !document.getElementById('skeleton-shimmer-style')) {
  const style = document.createElement('style');
  style.id = 'skeleton-shimmer-style';
  style.textContent = `
    @media (prefers-reduced-motion: no-preference) {
      @keyframes shimmer {
        0% { transform: translateX(-100%); }
        100% { transform: translateX(100%); }
      }
    }
    @media (prefers-reduced-motion: reduce) {
      @keyframes shimmer {
        0%, 100% { opacity: 1; }
      }
    }
  `;
  document.head.appendChild(style);
}
