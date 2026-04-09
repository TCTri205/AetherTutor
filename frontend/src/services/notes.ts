import api from './api';
import type {
  NoteCreate,
  NoteRead,
  NoteDetail,
  NoteUpdate,
  NoteListItem,
  NoteListResponse,
  NoteLinkCreate,
  NoteLinkResponse,
  BacklinkSuggestionsResponse,
  NoteGraphResponse,
} from '../types/api';

/**
 * Service for Zettelkasten notes and backlink API calls.
 */
export const notesService = {
  /**
   * Create a new note.
   */
  async create(note: NoteCreate): Promise<NoteRead> {
    const response = await api.post<NoteRead>('/notes', note);
    return response.data;
  },

  /**
   * List notes with pagination, filtering by note_type and tags.
   */
  async list(skip = 0, limit = 100, noteType?: string, tags?: string[]): Promise<NoteListResponse> {
    const response = await api.get<NoteListResponse>('/notes', {
      params: {
        skip,
        limit,
        ...(noteType && { note_type: noteType }),
        ...(tags && tags.length > 0 && { tags: tags.join(',') }),
      },
    });
    return response.data;
  },

  /**
   * Get note detail with backlinks.
   */
  async getById(noteId: string): Promise<NoteDetail> {
    const response = await api.get<NoteDetail>(`/notes/${noteId}`);
    return response.data;
  },

  /**
   * Update a note.
   */
  async update(noteId: string, note: NoteUpdate): Promise<NoteRead> {
    const response = await api.patch<NoteRead>(`/notes/${noteId}`, note);
    return response.data;
  },

  /**
   * Delete a note.
   */
  async delete(noteId: string): Promise<void> {
    await api.delete(`/notes/${noteId}`);
  },

  /**
   * Create a manual link between two notes.
   */
  async createLink(noteId: string, link: NoteLinkCreate): Promise<NoteLinkResponse> {
    const response = await api.post<NoteLinkResponse>(`/notes/${noteId}/links`, link);
    return response.data;
  },

  /**
   * Get incoming backlinks for a note.
   */
  async getBacklinks(noteId: string): Promise<NoteLinkResponse[]> {
    const response = await api.get<NoteLinkResponse[]>(`/notes/${noteId}/backlinks`);
    return response.data;
  },

  /**
   * Get AI-suggested backlinks for a note.
   */
  async suggestBacklinks(noteId: string): Promise<BacklinkSuggestionsResponse> {
    const response = await api.post<BacklinkSuggestionsResponse>(
      `/notes/${noteId}/suggest-backlinks`,
    );
    return response.data;
  },

  /**
   * Get the full note graph for React Flow visualization.
   */
  async getGraph(): Promise<NoteGraphResponse> {
    const response = await api.get<NoteGraphResponse>('/notes/graph');
    return response.data;
  },

  /**
   * Search notes by title/content.
   */
  async search(query: string, skip = 0, limit = 100): Promise<NoteListResponse> {
    const response = await api.get<NoteListResponse>('/notes/search', {
      params: { q: query, skip, limit },
    });
    return response.data;
  },
};
