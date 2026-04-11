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

  /**
   * Get global graph across documents.
   */
  async getGlobalGraph(scope: string = 'user_global', documentIds?: string[]): Promise<any> {
    const response = await api.post('/graph/global', {
      scope,
      document_ids: documentIds,
      top_k: 100,
      min_confidence: 0.1
    });
    return response.data;
  },

  /**
   * Get backlinks for an entity.
   */
  async getBacklinks(entityId: string): Promise<any[]> {
    const response = await api.get(`/graph/entities/${entityId}/backlinks`);
    return response.data;
  },

  /**
   * Get all tags.
   */
  async getTags(): Promise<string[]> {
    const response = await api.get('/graph/tags');
    return response.data;
  },

  /**
   * Get entities by tag.
   */
  async getEntitiesByTag(tag: string): Promise<any[]> {
    const response = await api.get(`/graph/tags/${tag}/entities`);
    return response.data;
  },
  
  /**
   * Export graph in specific format.
   */
  async exportGraph(documentId: string, format: 'graphml' | 'json' = 'graphml'): Promise<Blob> {
    const response = await api.get(`/graph/${documentId}/export`, {
      params: { format },
      responseType: 'blob'
    });
    return response.data;
  },

  /**
   * Merge two entities.
   */
  async mergeEntities(primaryId: string, secondaryId: string): Promise<any> {
    const response = await api.post('/graph/entities/merge', {
      primary_entity_id: primaryId,
      secondary_entity_id: secondaryId,
    });
    return response.data;
  },
};
