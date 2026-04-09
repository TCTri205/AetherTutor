import { create } from 'zustand';
import { flashcardService } from '../services/flashcards';
import type {
  FlashcardRead,
  FlashcardCreate,
  FlashcardUpdate,
  FlashcardReviewRequest,
  FlashcardReviewResponse,
  FlashcardStatsResponse,
} from '../types/api';

interface FlashcardState {
  cards: FlashcardRead[];
  dueCards: FlashcardRead[];
  stats: FlashcardStatsResponse | null;
  isLoading: boolean;
  isReviewing: boolean;
  error: string | null;

  // Actions
  fetchCards: () => Promise<void>;
  fetchDueCards: (limit?: number) => Promise<void>;
  fetchStats: () => Promise<void>;
  createCard: (card: FlashcardCreate) => Promise<FlashcardRead | null>;
  updateCard: (cardId: string, card: FlashcardUpdate) => Promise<void>;
  deleteCard: (cardId: string) => Promise<void>;
  submitReview: (review: FlashcardReviewRequest) => Promise<FlashcardReviewResponse | null>;
  generateFromDocument: (documentId: string) => Promise<number>;
  setCurrentCard: (card: FlashcardRead | null) => void;
  currentCard: FlashcardRead | null;
}

export const useFlashcardStore = create<FlashcardState>((set, get) => ({
  cards: [],
  dueCards: [],
  stats: null,
  isLoading: false,
  isReviewing: false,
  error: null,
  currentCard: null,

  fetchCards: async () => {
    set({ isLoading: true, error: null });
    try {
      const cards = await flashcardService.list(0, 200);
      set({ cards, isLoading: false });
    } catch (err: any) {
      set({ error: err.message, isLoading: false });
    }
  },

  fetchDueCards: async (limit = 50) => {
    set({ isLoading: true, error: null });
    try {
      const data = await flashcardService.getDue(limit);
      set({ dueCards: data.cards, isLoading: false });
    } catch (err: any) {
      set({ error: err.message, isLoading: false });
    }
  },

  fetchStats: async () => {
    try {
      const stats = await flashcardService.getStats();
      set({ stats });
    } catch (err: any) {
      set({ error: err.message });
    }
  },

  createCard: async (card: FlashcardCreate) => {
    try {
      const newCard = await flashcardService.create(card);
      set((state) => ({ cards: [newCard, ...state.cards] }));
      return newCard;
    } catch (err: any) {
      set({ error: err.message });
      return null;
    }
  },

  updateCard: async (cardId: string, card: FlashcardUpdate) => {
    try {
      const updated = await flashcardService.update(cardId, card);
      set((state) => ({
        cards: state.cards.map((c) => (c.id === cardId ? updated : c)),
        dueCards: state.dueCards.map((c) => (c.id === cardId ? updated : c)),
      }));
    } catch (err: any) {
      set({ error: err.message });
    }
  },

  deleteCard: async (cardId: string) => {
    try {
      await flashcardService.delete(cardId);
      set((state) => ({
        cards: state.cards.filter((c) => c.id !== cardId),
        dueCards: state.dueCards.filter((c) => c.id !== cardId),
      }));
    } catch (err: any) {
      set({ error: err.message });
    }
  },

  submitReview: async (review: FlashcardReviewRequest) => {
    try {
      const result = await flashcardService.review(review);
      // Update the reviewed card in dueCards
      set((state) => {
        const updatedCard = state.dueCards.find((c) => c.id === review.card_id);
        if (!updatedCard) return { dueCards: state.dueCards };
        const newCard = {
          ...updatedCard,
          sm2_ease_factor: result.ease_factor,
          sm2_interval: result.interval,
          sm2_repetitions: result.repetitions,
          sm2_next_review: result.next_review,
        };
        return {
          dueCards: state.dueCards.filter((c) => c.id !== review.card_id),
          currentCard:
            state.currentCard?.id === review.card_id ? null : state.currentCard,
        };
      });
      return result;
    } catch (err: any) {
      set({ error: err.message });
      return null;
    }
  },

  generateFromDocument: async (documentId: string) => {
    try {
      const result = await flashcardService.generate({ document_id: documentId });
      set((state) => ({ cards: [...result.cards, ...state.cards] }));
      return result.cards_created;
    } catch (err: any) {
      set({ error: err.message });
      return 0;
    }
  },

  setCurrentCard: (card: FlashcardRead | null) => {
    set({ currentCard: card });
  },
}));
