import { create } from 'zustand';
import { notesService } from '../services/notes';
import type {
  NoteListItem,
  NoteDetail,
  NoteCreate,
  NoteUpdate,
  NoteLinkResponse,
  BacklinkSuggestionsResponse,
  NoteGraphResponse,
  NoteListResponse,
} from '../types/api';

interface NotesState {
  notes: NoteListItem[];
  totalNotes: number;
  currentNote: NoteDetail | null;
  graph: NoteGraphResponse | null;
  backlinkSuggestions: BacklinkSuggestionsResponse | null;
  isLoading: boolean;
  error: string | null;

  // Search & filter
  searchQuery: string;
  selectedNoteType: string | null;
  selectedTags: string[];

  // Actions
  fetchNotes: () => Promise<void>;
  fetchNoteById: (noteId: string) => Promise<void>;
  createNote: (note: NoteCreate) => Promise<void>;
  updateNote: (noteId: string, note: NoteUpdate) => Promise<void>;
  deleteNote: (noteId: string) => Promise<void>;
  fetchBacklinks: (noteId: string) => Promise<NoteLinkResponse[]>;
  fetchBacklinkSuggestions: (noteId: string) => Promise<void>;
  fetchGraph: () => Promise<void>;
  searchNotes: (query: string) => Promise<void>;
  setSearchQuery: (query: string) => void;
  setSelectedNoteType: (type: string | null) => void;
  setSelectedTags: (tags: string[]) => void;
  setCurrentNote: (note: NoteDetail | null) => void;
  clearError: () => void;
}

export const useNotesStore = create<NotesState>((set, get) => ({
  notes: [],
  totalNotes: 0,
  currentNote: null,
  graph: null,
  backlinkSuggestions: null,
  isLoading: false,
  error: null,
  searchQuery: '',
  selectedNoteType: null,
  selectedTags: [],

  fetchNotes: async () => {
    const { selectedNoteType, selectedTags } = get();
    set({ isLoading: true, error: null });
    try {
      const data: NoteListResponse = await notesService.list(
        0,
        200,
        selectedNoteType || undefined,
        selectedTags.length > 0 ? selectedTags : undefined,
      );
      set({ notes: data.notes, totalNotes: data.total, isLoading: false });
    } catch (err: any) {
      set({ error: err.message, isLoading: false });
    }
  },

  fetchNoteById: async (noteId: string) => {
    set({ isLoading: true, error: null });
    try {
      const note = await notesService.getById(noteId);
      set({ currentNote: note, isLoading: false });
    } catch (err: any) {
      set({ error: err.message, isLoading: false });
    }
  },

  createNote: async (note: NoteCreate) => {
    try {
      await notesService.create(note);
      // Refresh notes list
      await get().fetchNotes();
    } catch (err: any) {
      set({ error: err.message });
    }
  },

  updateNote: async (noteId: string, note: NoteUpdate) => {
    try {
      await notesService.update(noteId, note);
      // Refresh current note
      await get().fetchNoteById(noteId);
      // Also refresh list
      await get().fetchNotes();
    } catch (err: any) {
      set({ error: err.message });
    }
  },

  deleteNote: async (noteId: string) => {
    try {
      await notesService.delete(noteId);
      set((state) => ({
        notes: state.notes.filter((n) => n.id !== noteId),
        currentNote: state.currentNote?.id === noteId ? null : state.currentNote,
      }));
    } catch (err: any) {
      set({ error: err.message });
    }
  },

  fetchBacklinks: async (noteId: string) => {
    try {
      const backlinks = await notesService.getBacklinks(noteId);
      return backlinks;
    } catch (err: any) {
      set({ error: err.message });
      return [];
    }
  },

  fetchBacklinkSuggestions: async (noteId: string) => {
    try {
      const suggestions = await notesService.suggestBacklinks(noteId);
      set({ backlinkSuggestions: suggestions });
    } catch (err: any) {
      set({ error: err.message });
    }
  },

  fetchGraph: async () => {
    set({ isLoading: true, error: null });
    try {
      const graph = await notesService.getGraph();
      set({ graph, isLoading: false });
    } catch (err: any) {
      set({ error: err.message, isLoading: false });
    }
  },

  searchNotes: async (query: string) => {
    set({ isLoading: true, error: null, searchQuery: query });
    try {
      const data: NoteListResponse = await notesService.search(query);
      set({ notes: data.notes, totalNotes: data.total, isLoading: false });
    } catch (err: any) {
      set({ error: err.message, isLoading: false });
    }
  },

  setSearchQuery: (query: string) => {
    set({ searchQuery: query });
  },

  setSelectedNoteType: (type: string | null) => {
    set({ selectedNoteType: type });
    get().fetchNotes();
  },

  setSelectedTags: (tags: string[]) => {
    set({ selectedTags: tags });
    get().fetchNotes();
  },

  setCurrentNote: (note: NoteDetail | null) => {
    set({ currentNote: note });
  },

  clearError: () => {
    set({ error: null });
  },
}));
