import api from './api';
import type { DocumentDetail, DocumentUploadResponse } from '../types/api';

/**
 * Service for document-related API calls.
 */
export const documentService = {
  /**
   * List all documents with pagination.
   */
  async listDocuments(skip = 0, limit = 100): Promise<DocumentDetail[]> {
    const response = await api.get<DocumentDetail[]>('/documents/', {
      params: { skip, limit },
    });
    return response.data;
  },

  /**
   * Upload a PDF file.
   * Returns 202 for new files, 200 for duplicates.
   */
  async uploadDocument(file: File): Promise<DocumentUploadResponse> {
    const formData = new FormData();
    formData.append('file', file);

    const response = await api.post<DocumentUploadResponse>('/documents/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },

  /**
   * Get detailed status of a specific document.
   */
  async getDocumentStatus(documentId: string): Promise<DocumentDetail> {
    const response = await api.get<DocumentDetail>(`/documents/${documentId}`);
    return response.data;
  },

  /**
   * Delete a document and its associated data.
   */
  async deleteDocument(documentId: string): Promise<{ message: string }> {
    const response = await api.delete<{ message: string }>(`/documents/${documentId}`);
    return response.data;
  },
};
