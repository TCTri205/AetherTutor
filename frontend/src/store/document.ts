import { create } from 'zustand';
import { documentService } from '../services/documents';
import type { DocumentDetail } from '../types/api';

interface DocumentState {
  documents: DocumentDetail[];
  isLoading: boolean;
  error: string | null;

  // Actions
  fetchDocuments: () => Promise<void>;
  updateDocumentStatus: (documentId: string, status: Partial<DocumentDetail>) => void;
  removeDocument: (documentId: string) => void;
}

export const useDocumentStore = create<DocumentState>((set, get) => ({
  documents: [],
  isLoading: false,
  error: null,

  fetchDocuments: async () => {
    set({ isLoading: true, error: null });
    try {
      const docs = await documentService.listDocuments();
      set({ documents: docs, isLoading: false });
    } catch (err: any) {
      set({ error: err.message, isLoading: false });
    }
  },

  updateDocumentStatus: (documentId, status) => {
    set((state) => ({
      documents: state.documents.map((doc) =>
        doc.id === documentId ? { ...doc, ...status } : doc
      ),
    }));
  },

  removeDocument: (documentId) => {
    set((state) => ({
      documents: state.documents.filter((doc) => doc.id !== documentId),
    }));
  },
}));
