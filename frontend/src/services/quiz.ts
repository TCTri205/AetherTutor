import api from './api';
import type {
  QuizGenerateRequest,
  QuizResponse,
  QuizListItemResponse,
  QuizSubmitRequest,
  QuizResultResponse,
  QuizStatsResponse,
  WeakAreasResponse,
  QuizResultListItemResponse,
  FlashcardSuggestionResponse,
  QuizFeedbackRequest,
} from '../types/api';

/**
 * Service for quiz examiner agent API calls.
 */
export const quizService = {
  /**
   * Generate a quiz from a document's knowledge graph.
   */
  async generate(request: QuizGenerateRequest): Promise<QuizResponse> {
    const response = await api.post<QuizResponse>('/quiz/generate', request);
    return response.data;
  },

  /**
   * Submit quiz answers for grading.
   */
  async submit(quizId: string, request: QuizSubmitRequest): Promise<QuizResultResponse> {
    const response = await api.post<QuizResultResponse>(`/quiz/${quizId}/submit`, request);
    return response.data;
  },

  /**
   * Get detailed quiz results.
   */
  async getResult(resultId: string): Promise<QuizResultResponse> {
    const response = await api.get<QuizResultResponse>(`/quiz/results/${resultId}`);
    return response.data;
  },

  /**
   * List user quizzes with pagination.
   */
  async list(skip = 0, limit = 100, documentId?: string): Promise<QuizListItemResponse[]> {
    const response = await api.get<QuizListItemResponse[]>('/quiz', {
      params: { skip, limit, ...(documentId && { document_id: documentId }) },
    });
    return response.data;
  },

  /**
   * Get quiz detail by ID.
   */
  async getById(quizId: string): Promise<QuizResponse> {
    const response = await api.get<QuizResponse>(`/quiz/${quizId}`);
    return response.data;
  },

  /**
   * Convert wrong answers from a quiz result to flashcard suggestions.
   */
  async convertToFlashcards(resultId: string): Promise<FlashcardSuggestionResponse[]> {
    const response = await api.post<FlashcardSuggestionResponse[]>(
      `/quiz/results/${resultId}/convert-to-flashcards`,
    );
    return response.data;
  },

  /**
   * Submit quality feedback for a quiz result.
   */
  async submitFeedback(resultId: string, request: QuizFeedbackRequest): Promise<{ status: string; message: string; quality_rating: number }> {
    const response = await api.post(`/quiz/results/${resultId}/feedback`, request);
    return response.data;
  },

  /**
   * Get user quiz statistics.
   */
  async getStats(): Promise<QuizStatsResponse> {
    const response = await api.get<QuizStatsResponse>('/quiz/stats');
    return response.data;
  },

  /**
   * Get weak areas based on quiz performance.
   */
  async getWeakAreas(limit = 10): Promise<WeakAreasResponse[]> {
    const response = await api.get<WeakAreasResponse[]>('/quiz/weak-areas', {
      params: { limit },
    });
    return response.data;
  },

  /**
   * Get list of quiz results (history).
   */
  async listResults(quizId: string, skip = 0, limit = 100): Promise<QuizResultListItemResponse[]> {
    const response = await api.get<QuizResultListItemResponse[]>(`/quiz/${quizId}/results`, {
      params: { skip, limit },
    });
    return response.data;
  },
};
