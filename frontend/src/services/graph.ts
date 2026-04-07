import api from './api';
import type { QueryResponse, GraphData, GraphStats } from '../types/api';

/**
 * Service for graph-related operations.
 */
export const graphService = {
  /**
   * Query the knowledge graph for a specific document or global context.
   */
  async queryGraph(query: string, documentId: string): Promise<QueryResponse> {
    const response = await api.post<QueryResponse>('/graph/query', {
      query,
      document_id: documentId,
    });
    return response.data;
  },

  /**
   * Get all nodes and edges for visualization.
   */
  async getDocumentGraph(documentId: string): Promise<GraphData> {
    const response = await api.get<GraphData>(`/graph/${documentId}/view`);
    return response.data;
  },

  /**
   * Get extraction stats (entity/relation counts).
   */
  async getGraphStats(documentId: string): Promise<GraphStats> {
    const response = await api.get<GraphStats>(`/graph/${documentId}/stats`);
    return response.data;
  },
};
