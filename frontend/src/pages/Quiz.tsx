import '../styles/tokens.css';
import { useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  FileQuestion,
  Plus,
  Play,
  CheckCircle,
  XCircle,
  ChevronLeft,
  ChevronRight,
  Loader2,
  BarChart3,
  Trophy,
  Target,
  AlertCircle,
  Clock,
  BookOpen,
  Eye,
  Brain,
  Sparkles,
  RefreshCcw,
} from 'lucide-react';
import { Button } from '../components/ui/Button';
import { Badge } from '../components/ui/Badge';
import { Card, CardContent } from '../components/ui/Card';
import { cn } from '../lib/utils';
import { toast } from 'sonner';
import { useQuizStore } from '../store/quiz';
import { useDocumentStore } from '../store/document';
import type { QuizGenerateRequest, QuizQuestionType, QuizDifficulty } from '../types/api';
import { formatDistanceToNow } from 'date-fns';
import { vi } from 'date-fns/locale';

type QuizPhase = 'list' | 'config' | 'taking' | 'results';

export default function Quiz() {
  const {
    quizzes,
    currentQuiz,
    currentQuizResult,
    stats,
    weakAreas,
    isLoading,
    isSubmitting,
    isQuizActive,
    quizAnswers,
    fetchQuizzes,
    fetchQuizById,
    generateQuiz,
    startQuiz,
    setAnswer,
    submitQuiz,
    fetchResult,
    fetchStats,
    fetchWeakAreas,
    resetQuiz,
  } = useQuizStore();

  const { documents, fetchDocuments } = useDocumentStore();

  const [phase, setPhase] = useState<QuizPhase>('list');
  const [questionIndex, setQuestionIndex] = useState(0);
  const [config, setConfig] = useState<QuizGenerateRequest>({
    num_questions: 10,
    question_types: ['multiple_choice', 'true_false'],
    difficulty: 3,
  });
  const [selectedDocId, setSelectedDocId] = useState<string>('');

  useEffect(() => {
    fetchQuizzes();
    fetchStats();
    fetchWeakAreas();
    fetchDocuments();
  }, [fetchQuizzes, fetchStats, fetchWeakAreas, fetchDocuments]);

  const handleGenerateQuiz = async () => {
    const req: QuizGenerateRequest = {
      ...config,
      document_id: selectedDocId || undefined,
    };
    const quiz = await generateQuiz(req);
    if (quiz) {
      toast.success(`Đã tạo quiz với ${quiz.questions.length} câu hỏi`);
      setPhase('taking');
      startQuiz(quiz);
      setQuestionIndex(0);
    }
  };

  const handleSubmitQuiz = async () => {
    if (!currentQuiz) return;
    const result = await submitQuiz(currentQuiz.id);
    if (result) {
      setPhase('results');
      toast.info(`Kết quả: ${result.score.toFixed(0)}% (${result.correct_count}/${result.total_questions})`);
    }
  };

  const handleViewResult = async (resultId: string) => {
    await fetchResult(resultId);
    setPhase('results');
  };

  const handleViewQuiz = async (quizId: string) => {
    await fetchQuizById(quizId);
    if (currentQuiz) {
      startQuiz(currentQuiz);
      setPhase('taking');
    }
  };

  const handleReset = () => {
    resetQuiz();
    setPhase('list');
    setQuestionIndex(0);
  };

  // ===== RESULTS PHASE =====
  if (phase === 'results' && currentQuizResult) {
    const result = currentQuizResult;
    const scoreColor = result.score >= 70 ? 'text-emerald-400' : result.score >= 50 ? 'text-orange-400' : 'text-red-400';

    return (
      <div className="flex flex-col gap-8 max-w-4xl mx-auto pb-20">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Button variant="ghost" onClick={handleReset}>
              <ChevronLeft className="w-4 h-4 mr-2" />
              Về danh sách
            </Button>
          </div>
          <Badge variant="outline">Kết quả Quiz</Badge>
        </div>

        {/* Score Overview */}
        <Card className="border-primary/20 bg-gradient-to-r from-primary/10 to-transparent">
          <CardContent className="p-8 text-center space-y-6">
            <div className={cn('text-6xl font-black', scoreColor)}>
              {result.score.toFixed(0)}%
            </div>
            <div className="grid grid-cols-3 gap-6">
              <div>
                <p className="text-xs text-muted-foreground">Đúng</p>
                <p className="text-2xl font-bold text-emerald-400">{result.correct_count}</p>
              </div>
              <div>
                <p className="text-xs text-muted-foreground">Sai</p>
                <p className="text-2xl font-bold text-red-400">{result.wrong_count}</p>
              </div>
              <div>
                <p className="text-xs text-secondary">Tổng</p>
                <p className="text-2xl font-bold text-primary">{result.total_questions}</p>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Weak Areas */}
        {result.weak_areas.length > 0 && (
          <Card className="border-orange-500/20">
            <CardContent className="p-6">
              <h3 className="font-bold text-primary mb-4 flex items-center gap-2">
                <Target className="w-5 h-5 text-orange-400" />
                Vùng cần cải thiện
              </h3>
              <div className="flex flex-wrap gap-2">
                {result.weak_areas.map((area, i) => (
                  <Badge key={i} variant="outline" className="px-3 py-1.5">
                    {area.entity_name}
                  </Badge>
                ))}
              </div>
            </CardContent>
          </Card>
        )}

        {/* Detailed Answers */}
        <div className="space-y-4">
          <h3 className="font-bold text-primary text-lg">Chi tiết từng câu</h3>
          {result.results.map((answer, i) => (
            <Card key={answer.question_id} className={cn(
              'border-border-primary',
              answer.is_correct ? 'border-emerald-500/10' : 'border-red-500/10',
            )}>
              <CardContent className="p-5 space-y-3">
                <div className="flex items-start justify-between gap-4">
                  <div className="flex items-center gap-3 flex-1">
                    {answer.is_correct
                      ? <CheckCircle className="w-5 h-5 text-emerald-400 shrink-0" />
                      : <XCircle className="w-5 h-5 text-red-400 shrink-0" />
                    }
                    <div className="flex-1">
                      <p className="font-semibold text-primary text-sm">Câu {i + 1}: {answer.question_text}</p>
                      <div className="flex gap-4 mt-2 text-xs text-secondary">
                        <span>Loại: {answer.question_type}</span>
                        <span>Độ khó: {answer.difficulty}/5</span>
                        <span>Bloom: {answer.bloom_level}</span>
                      </div>
                    </div>
                  </div>
                </div>
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div className="bg-red-500/5 border border-red-500/10 rounded-lg p-3">
                    <p className="text-[10px] text-red-400 uppercase mb-1">Trả lời</p>
                    <p className="text-primary">{answer.user_answer}</p>
                  </div>
                  <div className="bg-emerald-500/5 border border-emerald-500/10 rounded-lg p-3">
                    <p className="text-[10px] text-emerald-400 uppercase mb-1">Đáp án đúng</p>
                    <p className="text-primary">{answer.correct_answer}</p>
                  </div>
                </div>
                {answer.explanation && (
                  <div className="bg-secondary rounded-lg p-3 text-sm text-secondary">
                    <p className="text-[10px] text-secondary uppercase mb-1">Giải thích</p>
                    {answer.explanation}
                  </div>
                )}
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    );
  }

  // ===== TAKING QUIZ PHASE =====
  if (phase === 'taking' && currentQuiz) {
    const question = currentQuiz.questions[questionIndex];
    if (!question) {
      return <div className="text-center py-20">Không tìm thấy câu hỏi</div>;
    }

    const currentAnswer = quizAnswers[question.question_id] || '';
    const progress = ((questionIndex + 1) / currentQuiz.questions.length) * 100;

    return (
      <div className="flex flex-col gap-6 max-w-3xl mx-auto pb-20">
        {/* Header */}
        <div className="flex items-center justify-between">
          <Button variant="ghost" onClick={handleReset}>
            <ChevronLeft className="w-4 h-4 mr-2" />
            Hủy Quiz
          </Button>
          <div className="flex items-center gap-4">
            <Badge variant="outline">
              {questionIndex + 1} / {currentQuiz.questions.length}
            </Badge>
          </div>
        </div>

        {/* Progress bar */}
        <div className="w-full h-2 bg-secondary rounded-full overflow-hidden">
          <div
            className="h-full bg-primary transition-all duration-300 rounded-full"
            style={{ width: `${progress}%` }}
          />
        </div>

        {/* Question Card */}
        <Card className="border-primary/20">
          <CardContent className="p-8 space-y-6">
            <div className="flex items-center gap-3">
              <Badge variant="outline">{question.question_type === 'multiple_choice' ? 'Trắc nghiệm' : 'Đúng/Sai'}</Badge>
              <span className="text-xs text-secondary">Độ khó: {question.difficulty}/5</span>
              {question.entity_name && (
                <span className="text-xs text-secondary">• {question.entity_name}</span>
              )}
            </div>

            <h3 className="text-xl font-bold text-primary leading-relaxed">{question.question_text}</h3>

            {/* Options */}
            <div className="space-y-3">
              {question.question_type === 'multiple_choice' && question.options?.map((option, i) => (
                <button
                  key={i}
                  className={cn(
                    'w-full text-left p-4 rounded-xl border transition-all text-sm',
                    currentAnswer === option
                      ? 'border-primary bg-primary/10 text-primary'
                      : 'border-border-primary text-secondary hover:border-secondary hover:bg-secondary',
                  )}
                  onClick={() => setAnswer(question.question_id, option)}
                >
                  <span className="font-bold mr-3">{String.fromCharCode(65 + i)}.</span>
                  {option}
                </button>
              ))}

              {question.question_type === 'true_false' && (
                <div className="flex gap-4">
                  {['Đúng', 'Sai'].map((option) => (
                    <button
                      key={option}
                      className={cn(
                        'flex-1 p-4 rounded-xl border transition-all text-sm font-bold',
                        currentAnswer === option
                          ? option === 'Đúng'
                            ? 'border-emerald-500 bg-emerald-500/10 text-emerald-400'
                            : 'border-red-500 bg-red-500/10 text-red-400'
                          : 'border-border-primary text-secondary hover:border-secondary hover:bg-secondary',
                      )}
                      onClick={() => setAnswer(question.question_id, option)}
                    >
                      {option}
                    </button>
                  ))}
                </div>
              )}
            </div>
          </CardContent>
        </Card>

        {/* Navigation */}
        <div className="flex items-center justify-between">
          <Button
            variant="ghost"
            disabled={questionIndex === 0}
            onClick={() => setQuestionIndex((i) => i - 1)}
          >
            <ChevronLeft className="w-4 h-4 mr-2" />
            Trước
          </Button>

          {questionIndex === currentQuiz.questions.length - 1 ? (
            <Button
              size="lg"
              disabled={Object.keys(quizAnswers).length === 0}
              onClick={handleSubmitQuiz}
            >
              {isSubmitting ? (
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
              ) : (
                <CheckCircle className="w-4 h-4 mr-2" />
              )}
              Nộp bài
            </Button>
          ) : (
            <Button onClick={() => setQuestionIndex((i) => i + 1)}>
              Tiếp
              <ChevronRight className="w-4 h-4 ml-2" />
            </Button>
          )}
        </div>
      </div>
    );
  }

  // ===== CONFIG PHASE =====
  if (phase === 'config') {
    return (
      <div className="flex flex-col gap-8 max-w-2xl mx-auto pb-20">
        <div className="flex items-center gap-3">
          <Button variant="ghost" onClick={() => setPhase('list')}>
            <ChevronLeft className="w-4 h-4 mr-2" />
            Quay lại
          </Button>
        </div>

        <Card className="border-primary/20">
          <CardContent className="p-8 space-y-6">
            <h2 className="text-2xl font-bold text-primary flex items-center gap-3">
              <Sparkles className="w-6 h-6 text-primary" />
              Cấu hình Quiz
            </h2>

            {/* Document selector */}
            <div>
              <label className="text-sm text-secondary mb-2 block">Tài liệu nguồn (tùy chọn)</label>
              <select
                className="w-full bg-background border border-border rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-primary/40"
                value={selectedDocId}
                onChange={(e) => setSelectedDocId(e.target.value)}
              >
                <option value="">Không chọn (dùng knowledge graph toàn cục)</option>
                {documents.filter(d => d.status === 'COMPLETED').map(doc => (
                  <option key={doc.id} value={doc.id}>{doc.filename}</option>
                ))}
              </select>
            </div>

            {/* Number of questions */}
            <div>
              <label className="text-sm text-secondary mb-2 block">
                Số câu hỏi: {config.num_questions}
              </label>
              <input
                type="range"
                min={1}
                max={20}
                value={config.num_questions || 10}
                onChange={(e) => setConfig({ ...config, num_questions: parseInt(e.target.value) })}
                className="w-full accent-primary"
              />
              <div className="flex justify-between text-[10px] text-secondary">
                <span>1</span>
                <span>20</span>
              </div>
            </div>

            {/* Question types */}
            <div>
              <label className="text-sm text-secondary mb-2 block">Loại câu hỏi</label>
              <div className="flex gap-3">
                {(['multiple_choice', 'true_false'] as QuizQuestionType[]).map((type) => (
                  <label
                    key={type}
                    className={cn(
                      'flex-1 p-3 rounded-xl border cursor-pointer text-sm text-center transition-all',
                      config.question_types?.includes(type)
                        ? 'border-primary bg-primary/10 text-primary'
                        : 'border-border-primary text-secondary hover:border-secondary',
                    )}
                  >
                    <input
                      type="checkbox"
                      className="hidden"
                      checked={config.question_types?.includes(type)}
                      onChange={(e) => {
                        const types = e.target.checked
                          ? [...(config.question_types || []), type]
                          : config.question_types?.filter((t) => t !== type) || [];
                        setConfig({ ...config, question_types: types });
                      }}
                    />
                    {type === 'multiple_choice' ? 'Trắc nghiệm' : 'Đúng/Sai'}
                  </label>
                ))}
              </div>
            </div>

            {/* Difficulty */}
            <div>
              <label className="text-sm text-secondary mb-2 block">
                Độ khó: {config.difficulty}/5
              </label>
              <div className="flex gap-2">
                {([1, 2, 3, 4, 5] as QuizDifficulty[]).map((d) => (
                  <button
                    key={d}
                    className={cn(
                      'flex-1 py-2 rounded-lg border text-sm font-bold transition-all',
                      config.difficulty === d
                        ? 'border-primary bg-primary/20 text-primary'
                        : 'border-border-primary text-secondary hover:border-secondary',
                    )}
                    onClick={() => setConfig({ ...config, difficulty: d })}
                  >
                    {d}
                  </button>
                ))}
              </div>
            </div>

            <Button size="lg" className="w-full" onClick={handleGenerateQuiz} disabled={isLoading}>
              {isLoading ? (
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
              ) : (
                <Play className="w-4 h-4 mr-2" />
              )}
              Tạo và Bắt đầu Quiz
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  // ===== LIST PHASE =====
  return (
    <div className="flex flex-col gap-8 max-w-5xl mx-auto pb-20">
      {/* Header */}
      <section className="flex flex-col md:flex-row justify-between items-start md:items-center gap-6">
        <div className="space-y-2">
          <h2 className="text-3xl font-bold text-primary tracking-tight flex items-center gap-3">
            <FileQuestion className="w-8 h-8 text-primary" />
            Quiz Examiner
          </h2>
          <p className="text-secondary">
            Kiểm tra kiến thức với AI-generated quizzes.
          </p>
        </div>
        <Button size="lg" onClick={() => setPhase('config')}>
          <Plus className="w-4 h-4 mr-2" />
          Tạo Quiz mới
        </Button>
      </section>

      {/* Stats */}
      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {[
            { label: 'Tổng quiz', value: stats.total_quizzes, icon: FileQuestion, color: 'text-blue-400' },
            { label: 'Điểm TB', value: `${stats.average_score.toFixed(0)}%`, icon: Trophy, color: 'text-yellow-400' },
            { label: 'Đã trả lời', value: stats.total_questions_answered, icon: BookOpen, color: 'text-emerald-400' },
            { label: 'Chính xác', value: `${stats.overall_accuracy.toFixed(0)}%`, icon: Target, color: 'text-purple-400' },
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

      {/* Weak Areas */}
      {weakAreas.length > 0 && (
        <Card className="border-orange-500/20">
          <CardContent className="p-6">
            <h3 className="font-bold text-primary mb-3 flex items-center gap-2">
              <AlertCircle className="w-5 h-5 text-orange-400" />
              Vùng kiến thức cần cải thiện
            </h3>
            <div className="flex flex-wrap gap-2">
              {weakAreas.slice(0, 10).map((area, i) => (
                <Badge key={i} variant="outline" className="px-3 py-1.5">
                  {area.entity_name}
                </Badge>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Quiz List */}
      <div className="space-y-4">
        <h3 className="font-bold text-primary text-lg">Quiz đã tạo</h3>
        {isLoading && quizzes.length === 0
          ? Array.from({ length: 3 }).map((_, i) => (
              <Card key={i} className="h-20 border-border-primary">
                <CardContent className="p-5 animate-pulse">
                  <div className="h-4 bg-tertiary rounded w-1/3" />
                </CardContent>
              </Card>
            ))
          : quizzes.map((quiz) => (
              <Card key={quiz.id} className="border-border-primary hover:border-primary/20 transition-all group">
                <CardContent className="p-5 flex items-center justify-between">
                  <div className="flex-1 min-w-0">
                    <h4 className="font-bold text-primary truncate">{quiz.title}</h4>
                    <div className="flex items-center gap-4 text-xs text-secondary mt-1">
                      <span>{quiz.num_questions} câu hỏi</span>
                      <span>Độ khó: {quiz.difficulty}/5</span>
                      <span className="flex items-center gap-1">
                        <Clock className="w-3 h-3" />
                        {formatDistanceToNow(new Date(quiz.created_at), { locale: vi })}
                      </span>
                    </div>
                  </div>
                  <div className="flex gap-2">
                    <Button variant="secondary" size="sm" onClick={() => handleViewQuiz(quiz.id)}>
                      <Play className="w-3.5 h-3.5" />
                    </Button>
                  </div>
                </CardContent>
              </Card>
            ))}
      </div>

      {/* Empty state */}
      {!isLoading && quizzes.length === 0 && (
        <div className="flex flex-col items-center justify-center py-20 bg-secondary border-2 border-dashed border-border-primary rounded-3xl gap-6">
          <div className="w-20 h-20 rounded-full bg-tertiary flex items-center justify-center border border-border-primary">
            <FileQuestion className="w-10 h-10 text-tertiary opacity-30" />
          </div>
          <div className="text-center space-y-2">
            <p className="text-primary font-bold text-lg">Chưa có quiz nào</p>
            <p className="text-secondary">Tạo quiz mới để kiểm tra kiến thức của bạn.</p>
          </div>
          <Button size="lg" onClick={() => setPhase('config')}>
            <Sparkles className="w-4 h-4 mr-2" />
            Tạo Quiz đầu tiên
          </Button>
        </div>
      )}
    </div>
  );
}
