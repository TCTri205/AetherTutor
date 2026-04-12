import '../styles/tokens.css';
import { useEffect, useState, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Brain,
  Plus,
  Sparkles,
  Clock,
  TrendingUp,
  BookOpen,
  RotateCcw,
  CheckCircle,
  XCircle,
  ChevronLeft,
  ChevronRight,
  Grid3X3,
  Play,
  Trash2,
  Edit,
  Loader2,
  FileText,
  Zap,
} from 'lucide-react';
import { Button } from '../components/ui/Button';
import { Badge } from '../components/ui/Badge';
import { Card, CardContent } from '../components/ui/Card';
import { cn } from '../lib/utils';
import { toast } from 'sonner';
import { useFlashcardStore } from '../store/flashcard';
import type { FlashcardRead, FlashcardCreate, FlashcardSource } from '../types/api';
import { formatDistanceToNow } from 'date-fns';
import { vi } from 'date-fns/locale';

type ViewMode = 'grid' | 'review';
type ReviewQuality = 0 | 2 | 3 | 5; // Again, Hard, Good, Easy

const QUALITY_LABELS: Record<ReviewQuality, { label: string; color: string; bg: string }> = {
  0: { label: 'Lại', color: 'text-red-400', bg: 'bg-red-500/10 hover:bg-red-500/20 border-red-500/30' },
  2: { label: 'Khó', color: 'text-orange-400', bg: 'bg-orange-500/10 hover:bg-orange-500/20 border-orange-500/30' },
  3: { label: 'Tốt', color: 'text-blue-400', bg: 'bg-blue-500/10 hover:bg-blue-500/20 border-blue-500/30' },
  5: { label: 'Dễ', color: 'text-emerald-400', bg: 'bg-emerald-500/10 hover:bg-emerald-500/20 border-emerald-500/30' },
};

const SOURCE_LABELS: Record<FlashcardSource, string> = {
  manual: 'Thủ công',
  quiz_wrong_answer: 'Từ Quiz',
  auto_generated: 'Tự động',
};

export default function Flashcards() {
  const {
    cards,
    dueCards,
    stats,
    isLoading,
    currentCard,
    fetchCards,
    fetchDueCards,
    fetchStats,
    createCard,
    deleteCard,
    submitReview,
    generateFromDocument,
    setCurrentCard,
  } = useFlashcardStore();

  const [viewMode, setViewMode] = useState<ViewMode>('grid');
  const [reviewIndex, setReviewIndex] = useState(0);
  const [isFlipped, setIsFlipped] = useState(false);
  const [showCreateDialog, setShowCreateDialog] = useState(false);
  const [createForm, setCreateForm] = useState<FlashcardCreate>({
    front: '',
    back: '',
    source: 'manual',
  });

  useEffect(() => {
    fetchCards();
    fetchDueCards();
    fetchStats();
  }, [fetchCards, fetchDueCards, fetchStats]);

  const handleStartReview = () => {
    if (dueCards.length === 0) {
      toast.info('Không có thẻ cần ôn tập!');
      return;
    }
    setReviewIndex(0);
    setIsFlipped(false);
    setViewMode('review');
  };

  const handleReview = useCallback(async (quality: ReviewQuality) => {
    if (!currentCard && reviewIndex >= dueCards.length) return;
    const card = currentCard || dueCards[reviewIndex];
    if (!card) return;

    const result = await submitReview({ card_id: card.id, quality });
    if (result) {
      setIsFlipped(false);
      // Move to next card
      if (reviewIndex < dueCards.length - 1) {
        setReviewIndex((i) => i + 1);
      } else {
        toast.success('🎉 Đã ôn hết các thẻ hôm nay!');
        setViewMode('grid');
        fetchDueCards();
        fetchStats();
      }
    }
  }, [currentCard, reviewIndex, dueCards, submitReview, fetchDueCards, fetchStats]);

  const handleCreateCard = async () => {
    if (!createForm.front.trim() || !createForm.back.trim()) {
      toast.error('Vui lòng điền đầy đủ mặt trước và mặt sau');
      return;
    }
    const card = await createCard(createForm);
    if (card) {
      toast.success('Đã tạo flashcard mới');
      setShowCreateDialog(false);
      setCreateForm({ front: '', back: '', source: 'manual' });
    }
  };

  const handleDeleteCard = async (cardId: string) => {
    if (!confirm('Xóa flashcard này?')) return;
    await deleteCard(cardId);
    toast.success('Đã xóa flashcard');
  };

  const handleGenerateFromDocument = async () => {
    const documentId = prompt('Nhập Document ID để sinh flashcard:');
    if (!documentId) return;
    const count = await generateFromDocument(documentId);
    if (count > 0) {
      toast.success(`Đã tạo ${count} flashcard từ tài liệu`);
    }
  };

  // ===== REVIEW MODE =====
  if (viewMode === 'review') {
    const card = currentCard || dueCards[reviewIndex];

    if (!card) {
      return (
        <div className="flex flex-col items-center justify-center h-full gap-8">
          <div className="text-center space-y-4">
            <h2 className="text-3xl font-bold text-primary">Ôn tập Flashcard</h2>
            <p className="text-secondary">
              {dueCards.length === 0
                ? 'Không có thẻ cần ôn tập. Thêm thẻ mới hoặc tạo từ tài liệu.'
                : 'Đã ôn hết các thẻ cần review!'}
            </p>
          </div>
          <div className="flex gap-4">
            <Button size="lg" onClick={() => setViewMode('grid')}>
              <ChevronLeft className="w-4 h-4 mr-2" />
              Về Grid View
            </Button>
          </div>
        </div>
      );
    }

    return (
      <div className="flex flex-col items-center justify-center h-full gap-6 max-w-3xl mx-auto w-full">
        {/* Review Header */}
        <div className="flex items-center justify-between w-full">
          <Button variant="ghost" onClick={() => { setViewMode('grid'); setCurrentCard(null); }}>
            <ChevronLeft className="w-4 h-4 mr-2" />
            Thoát Review
          </Button>
          <Badge variant="outline">
            {reviewIndex + 1} / {dueCards.length}
          </Badge>
        </div>

        {/* Card */}
        <motion.div
          key={card.id}
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -20 }}
          className="w-full"
        >
          <div
            className="relative cursor-pointer perspective-1000"
            onClick={() => setIsFlipped(!isFlipped)}
          >
            <motion.div
              animate={{ rotateY: isFlipped ? 180 : 0 }}
              transition={{ duration: 0.5, type: 'spring', stiffness: 200 }}
              className="w-full min-h-[320px]"
              style={{ transformStyle: 'preserve-3d' }}
            >
              {/* Front */}
              <div
                className="absolute inset-0"
                style={{ backfaceVisibility: 'hidden' }}
              >
                <Card className="h-full border-primary/20 bg-gradient-to-br from-secondary to-tertiary">
                  <CardContent className="flex flex-col items-center justify-center h-full p-12 text-center">
                    <Badge variant="outline" className="mb-6">{SOURCE_LABELS[card.source]}</Badge>
                    <h3 className="text-2xl font-bold text-primary leading-relaxed">{card.front}</h3>
                    <p className="text-sm text-secondary mt-8">Click để xem đáp án</p>
                  </CardContent>
                </Card>
              </div>

              {/* Back */}
              <div
                className="absolute inset-0"
                style={{ transform: 'rotateY(180deg)', backfaceVisibility: 'hidden' }}
              >
                <Card className="h-full border-emerald-500/20 bg-gradient-to-br from-emerald-500/5 to-tertiary">
                  <CardContent className="flex flex-col items-center justify-center h-full p-12 text-center">
                    <Badge variant="success" className="mb-6">Đáp án</Badge>
                    <p className="text-xl text-primary leading-relaxed whitespace-pre-wrap">{card.back}</p>
                    <div className="flex gap-6 mt-8 text-xs text-secondary">
                      <span>Ease: {card.sm2_ease_factor.toFixed(1)}</span>
                      <span>Interval: {card.sm2_interval}d</span>
                      <span>Reps: {card.sm2_repetitions}</span>
                    </div>
                  </CardContent>
                </Card>
              </div>
            </motion.div>
          </div>
        </motion.div>

        {/* Quality Buttons (only visible after flip) */}
        <AnimatePresence>
          {isFlipped && (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: 10 }}
              className="flex gap-3 w-full max-w-lg"
            >
              {(Object.keys(QUALITY_LABELS) as unknown as ReviewQuality[]).map(
                (quality) => {
                  const { label, color, bg } = QUALITY_LABELS[quality];
                  return (
                    <Button
                      key={quality}
                      variant="outline"
                      className={cn('flex-1 flex-col py-4 gap-1 border', bg)}
                      onClick={() => handleReview(quality)}
                    >
                      <span className={cn('font-bold text-sm', color)}>{label}</span>
                      <span className="text-[10px] text-secondary">
                        {quality}
                      </span>
                    </Button>
                  );
                },
              )}
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    );
  }

  // ===== GRID MODE =====
  return (
    <div className="flex flex-col gap-8 max-w-7xl mx-auto pb-20">
      {/* Header */}
      <section className="flex flex-col md:flex-row justify-between items-start md:items-center gap-6">
        <div className="space-y-2">
          <h2 className="text-3xl font-bold text-primary tracking-tight flex items-center gap-3">
            <Brain className="w-8 h-8 text-primary" />
            Flashcard SM-2
          </h2>
          <p className="text-secondary">
            Hệ thống lặp lại ngắt quãng — tối ưu ghi nhớ dài hạn.
          </p>
        </div>
        <div className="flex gap-3">
          <Button variant="outline" size="lg" onClick={handleGenerateFromDocument}>
            <Sparkles className="w-4 h-4 mr-2" />
            Sinh từ Document
          </Button>
          <Button size="lg" onClick={() => setShowCreateDialog(true)}>
            <Plus className="w-4 h-4 mr-2" />
            Tạo Flashcard
          </Button>
        </div>
      </section>

      {/* Stats Row */}
      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {[
            { label: 'Tổng thẻ', value: stats.total_cards, icon: BookOpen, color: 'text-blue-400' },
            { label: 'Cần ôn', value: stats.due_cards, icon: Clock, color: 'text-orange-400' },
            { label: 'Đã ôn', value: stats.total_reviews, icon: CheckCircle, color: 'text-emerald-400' },
            { label: 'Streak', value: `${stats.streak_days} ngày`, icon: Zap, color: 'text-yellow-400' },
          ].map(({ label, value, icon: Icon, color }) => (
            <Card key={label} className="border-border-primary bg-secondary">
              <CardContent className="p-4 flex items-center gap-3">
                <Icon className={cn('w-5 h-5', color)} />
                <div>
                  <p className="text-xs text-secondary">{label}</p>
                  <p className="text-xl font-bold text-primary">{value}</p>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Review Banner */}
      {dueCards.length > 0 && (
        <Card className="border-primary/30 bg-gradient-to-r from-primary/10 to-transparent">
          <CardContent className="p-6 flex items-center justify-between">
            <div className="flex items-center gap-4">
              <div className="w-12 h-12 rounded-xl bg-primary/20 flex items-center justify-center">
                <Play className="w-6 h-6 text-primary" />
              </div>
              <div>
                <p className="font-bold text-primary">{dueCards.length} thẻ cần ôn tập</p>
                <p className="text-sm text-secondary">Bắt đầu review để duy trì streak</p>
              </div>
            </div>
            <Button size="lg" className="bg-primary hover:bg-primary/80" onClick={handleStartReview}>
              <Brain className="w-4 h-4 mr-2" />
              Bắt đầu Review
            </Button>
          </CardContent>
        </Card>
      )}

      {/* Create Dialog */}
      {showCreateDialog && (
        <div className="fixed inset-0 bg-overlay z-50 flex items-center justify-center p-4">
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            className="w-full max-w-lg"
          >
            <Card className="border-border-primary">
              <CardContent className="p-6 space-y-4">
                <h3 className="text-xl font-bold text-primary">Tạo Flashcard mới</h3>
                <div className="space-y-3">
                  <div>
                    <label className="text-sm text-secondary mb-1 block">Mặt trước (Câu hỏi)</label>
                    <textarea
                      className="w-full bg-background border border-border rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-primary/40 resize-none"
                      rows={3}
                      placeholder="VD: SM-2 algorithm là gì?"
                      value={createForm.front}
                      onChange={(e) => setCreateForm({ ...createForm, front: e.target.value })}
                    />
                  </div>
                  <div>
                    <label className="text-sm text-secondary mb-1 block">Mặt sau (Đáp án)</label>
                    <textarea
                      className="w-full bg-background border border-border rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-primary/40 resize-none"
                      rows={4}
                      placeholder="VD: SM-2 là thuật toán spaced repetition..."
                      value={createForm.back}
                      onChange={(e) => setCreateForm({ ...createForm, back: e.target.value })}
                    />
                  </div>
                  <div>
                    <label className="text-sm text-secondary mb-1 block">Nguồn</label>
                    <select
                      className="w-full bg-background border border-border rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-primary/40"
                      value={createForm.source}
                      onChange={(e) => setCreateForm({ ...createForm, source: e.target.value as FlashcardSource })}
                    >
                      <option value="manual">Thủ công</option>
                      <option value="auto_generated">Tự động</option>
                      <option value="quiz_wrong_answer">Từ Quiz sai</option>
                    </select>
                  </div>
                </div>
                <div className="flex gap-3 justify-end">
                  <Button variant="ghost" onClick={() => setShowCreateDialog(false)}>Hủy</Button>
                  <Button onClick={handleCreateCard} disabled={!createForm.front.trim() || !createForm.back.trim()}>
                    Tạo thẻ
                  </Button>
                </div>
              </CardContent>
            </Card>
          </motion.div>
        </div>
      )}

      {/* Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {isLoading && cards.length === 0
          ? Array.from({ length: 6 }).map((_, i) => (
              <Card key={i} className="h-40 border-border-primary">
                <CardContent className="p-6 animate-pulse">
                  <div className="h-4 bg-tertiary rounded w-3/4 mb-3" />
                  <div className="h-3 bg-secondary rounded w-1/2" />
                </CardContent>
              </Card>
            ))
          : cards.map((card) => (
              <Card key={card.id} className="border-border-primary hover:border-primary/20 transition-all group">
                <CardContent className="p-5 space-y-3">
                  <div className="flex items-start justify-between">
                    <h4 className="font-semibold text-primary text-sm line-clamp-2 flex-1">{card.front}</h4>
                    <div className="flex gap-1 ml-2 shrink-0 opacity-0 group-hover:opacity-100 transition-opacity">
                      <Button variant="ghost" size="icon" className="h-7 w-7" onClick={() => { setCurrentCard(card); setViewMode('review'); }}>
                        <RotateCcw className="w-3.5 h-3.5" />
                      </Button>
                      <Button variant="ghost" size="icon" className="h-7 w-7 text-destructive/70" onClick={() => handleDeleteCard(card.id)}>
                        <Trash2 className="w-3.5 h-3.5" />
                      </Button>
                    </div>
                  </div>
                  <p className="text-xs text-secondary line-clamp-2">{card.back}</p>
                  <div className="flex items-center justify-between text-[10px] text-secondary">
                    <Badge variant="outline" className="text-[10px]">{SOURCE_LABELS[card.source]}</Badge>
                    <span className="flex items-center gap-1">
                      <Clock className="w-3 h-3" />
                      {formatDistanceToNow(new Date(card.sm2_next_review), { locale: vi })}
                    </span>
                  </div>
                  <div className="flex gap-2 text-[10px] text-secondary">
                    <span>Ease: {card.sm2_ease_factor.toFixed(1)}</span>
                    <span>•</span>
                    <span>Interval: {card.sm2_interval}d</span>
                    <span>•</span>
                    <span>Reps: {card.sm2_repetitions}</span>
                  </div>
                </CardContent>
              </Card>
            ))}
      </div>

      {/* Empty state */}
      {!isLoading && cards.length === 0 && (
        <div className="flex flex-col items-center justify-center py-20 bg-secondary border-2 border-dashed border-border-primary rounded-3xl gap-6">
          <div className="w-20 h-20 rounded-full bg-tertiary flex items-center justify-center border border-border-primary">
            <Brain className="w-10 h-10 text-tertiary opacity-30" />
          </div>
          <div className="text-center space-y-2">
            <p className="text-primary font-bold text-lg">Chưa có flashcard nào</p>
            <p className="text-secondary">Tạo flashcard thủ công hoặc sinh tự động từ tài liệu.</p>
          </div>
          <div className="flex gap-3">
            <Button variant="outline" onClick={() => setShowCreateDialog(true)}>
              <Plus className="w-4 h-4 mr-2" />
              Tạo Flashcard
            </Button>
            <Button onClick={handleGenerateFromDocument}>
              <Sparkles className="w-4 h-4 mr-2" />
              Sinh từ Document
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
