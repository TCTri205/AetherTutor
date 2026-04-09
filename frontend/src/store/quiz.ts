import { create } from 'zustand';
import { quizService } from '../services/quiz';
import type {
  QuizResponse,
  QuizListItemResponse,
  QuizResultResponse,
  QuizStatsResponse,
  WeakAreasResponse,
  QuizGenerateRequest,
  QuizQuestionResponse,
} from '../types/api';

interface QuizState {
  quizzes: QuizListItemResponse[];
  currentQuiz: QuizResponse | null;
  currentQuizResult: QuizResultResponse | null;
  stats: QuizStatsResponse | null;
  weakAreas: WeakAreasResponse[];
  isLoading: boolean;
  isSubmitting: boolean;
  error: string | null;

  // Quiz session state
  quizAnswers: Record<string, string>; // question_id -> answer
  isQuizActive: boolean;

  // Actions
  fetchQuizzes: () => Promise<void>;
  fetchQuizById: (quizId: string) => Promise<void>;
  generateQuiz: (request: QuizGenerateRequest) => Promise<QuizResponse | null>;
  startQuiz: (quiz: QuizResponse) => void;
  setAnswer: (questionId: string, answer: string) => void;
  submitQuiz: (quizId: string) => Promise<QuizResultResponse | null>;
  fetchResult: (resultId: string) => Promise<void>;
  fetchStats: () => Promise<void>;
  fetchWeakAreas: (limit?: number) => Promise<void>;
  resetQuiz: () => void;
  clearError: () => void;
}

export const useQuizStore = create<QuizState>((set, get) => ({
  quizzes: [],
  currentQuiz: null,
  currentQuizResult: null,
  stats: null,
  weakAreas: [],
  isLoading: false,
  isSubmitting: false,
  error: null,
  quizAnswers: {},
  isQuizActive: false,

  fetchQuizzes: async () => {
    set({ isLoading: true, error: null });
    try {
      const quizzes = await quizService.list(0, 100);
      set({ quizzes, isLoading: false });
    } catch (err: any) {
      set({ error: err.message, isLoading: false });
    }
  },

  fetchQuizById: async (quizId: string) => {
    set({ isLoading: true, error: null });
    try {
      const quiz = await quizService.getById(quizId);
      set({ currentQuiz: quiz, isLoading: false });
    } catch (err: any) {
      set({ error: err.message, isLoading: false });
    }
  },

  generateQuiz: async (request: QuizGenerateRequest) => {
    set({ isLoading: true, error: null });
    try {
      const quiz = await quizService.generate(request);
      set({ currentQuiz: quiz, isLoading: false });
      return quiz;
    } catch (err: any) {
      set({ error: err.message, isLoading: false });
      return null;
    }
  },

  startQuiz: (quiz: QuizResponse) => {
    set({
      currentQuiz: quiz,
      isQuizActive: true,
      quizAnswers: {},
      currentQuizResult: null,
    });
  },

  setAnswer: (questionId: string, answer: string) => {
    set((state) => ({
      quizAnswers: { ...state.quizAnswers, [questionId]: answer },
    }));
  },

  submitQuiz: async (quizId: string) => {
    const { quizAnswers } = get();
    const answers = Object.entries(quizAnswers).map(([question_id, answer]) => ({
      question_id,
      answer,
    }));

    if (answers.length === 0) {
      set({ error: 'Chưa trả lời câu hỏi nào' });
      return null;
    }

    set({ isSubmitting: true, error: null });
    try {
      const result = await quizService.submit(quizId, { answers });
      set({ currentQuizResult: result, isQuizActive: false, isSubmitting: false });
      return result;
    } catch (err: any) {
      set({ error: err.message, isSubmitting: false });
      return null;
    }
  },

  fetchResult: async (resultId: string) => {
    set({ isLoading: true, error: null });
    try {
      const result = await quizService.getResult(resultId);
      set({ currentQuizResult: result, isLoading: false });
    } catch (err: any) {
      set({ error: err.message, isLoading: false });
    }
  },

  fetchStats: async () => {
    try {
      const stats = await quizService.getStats();
      set({ stats });
    } catch (err: any) {
      set({ error: err.message });
    }
  },

  fetchWeakAreas: async (limit = 10) => {
    try {
      const areas = await quizService.getWeakAreas(limit);
      set({ weakAreas: areas });
    } catch (err: any) {
      set({ error: err.message });
    }
  },

  resetQuiz: () => {
    set({
      currentQuiz: null,
      currentQuizResult: null,
      quizAnswers: {},
      isQuizActive: false,
      error: null,
    });
  },

  clearError: () => {
    set({ error: null });
  },
}));
