import api from './api';
import type {
  FlashcardRead,
  FlashcardCreate,
  FlashcardUpdate,
  FlashcardDueResponse,
  FlashcardReviewRequest,
  FlashcardReviewResponse,
  FlashcardStatsResponse,
  FlashcardBulkGenerateRequest,
  FlashcardBulkGenerateResponse,
} from '../types/api';

/**
 * Service for flashcard SM-2 spaced repetition API calls.
 */
export const flashcardService = {
  /**
   * Get flashcards due for review.
   */
  async getDue(limit = 50): Promise<FlashcardDueResponse> {
    const response = await api.get<FlashcardDueResponse>('/flashcards/due', {
      params: { limit },
    });
    return response.data;
  },

  /**
   * Submit an SM-2 review for a flashcard.
   */
  async review(review: FlashcardReviewRequest): Promise<FlashcardReviewResponse> {
    const response = await api.post<FlashcardReviewResponse>('/flashcards/review', review);
    return response.data;
  },

  /**
   * Create a manual flashcard.
   */
  async create(card: FlashcardCreate): Promise<FlashcardRead> {
    const response = await api.post<FlashcardRead>('/flashcards', card);
    return response.data;
  },

  /**
   * List user flashcards with pagination and source filter.
   */
  async list(skip = 0, limit = 100, source?: string): Promise<FlashcardRead[]> {
    const response = await api.get<FlashcardRead[]>('/flashcards', {
      params: { skip, limit, ...(source && { source }) },
    });
    return response.data;
  },

  /**
   * Get a single flashcard by ID.
   */
  async getById(cardId: string): Promise<FlashcardRead> {
    const response = await api.get<FlashcardRead>(`/flashcards/${cardId}`);
    return response.data;
  },

  /**
   * Update a flashcard.
   */
  async update(cardId: string, card: FlashcardUpdate): Promise<FlashcardRead> {
    const response = await api.patch<FlashcardRead>(`/flashcards/${cardId}`, card);
    return response.data;
  },

  /**
   * Delete a flashcard.
   */
  async delete(cardId: string): Promise<void> {
    await api.delete(`/flashcards/${cardId}`);
  },

  /**
   * Get learning statistics (stats).
   */
  async getStats(): Promise<FlashcardStatsResponse> {
    const response = await api.get<FlashcardStatsResponse>('/flashcards/stats');
    return response.data;
  },

  /**
   * Auto-generate flashcards from a document.
   */
  async generate(request: FlashcardBulkGenerateRequest): Promise<FlashcardBulkGenerateResponse> {
    const response = await api.post<FlashcardBulkGenerateResponse>('/flashcards/generate', request);
    return response.data;
  },
};
