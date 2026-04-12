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

  // =========================================================================
  // Stage 3: Interactive Graph Editing — CRUD API
  // =========================================================================

  /**
   * Create a new entity.
   */
  async createEntity(data: {
    canonical_name: string;
    entity_type: string;
    description?: string;
    confidence?: number;
    source?: string;
    tags?: string[];
    metadata?: Record<string, unknown>;
  }): Promise<any> {
    const response = await api.post('/graph/entities', data);
    return response.data;
  },

  /**
   * Update an entity with optimistic concurrency.
   */
  async updateEntity(
    entityId: string,
    data: {
      expected_version: number;
      canonical_name?: string;
      entity_type?: string;
      description?: string;
      source?: string;
      tags?: string[];
      metadata?: Record<string, unknown>;
    }
  ): Promise<any> {
    const response = await api.put(`/graph/entities/${entityId}`, data);
    return response.data;
  },

  /**
   * Delete an entity.
   */
  async deleteEntity(entityId: string, expectedVersion: number): Promise<void> {
    await api.delete(`/graph/entities/${entityId}`, {
      params: { expected_version: expectedVersion },
    });
  },

  /**
   * Create a new relation.
   */
  async createRelation(data: {
    source_entity_id: string;
    target_entity_id: string;
    relation_type: string;
    description?: string;
    source?: string;
  }): Promise<any> {
    const response = await api.post('/graph/relations', data);
    return response.data;
  },

  /**
   * Delete a relation.
   */
  async deleteRelation(relationId: string, expectedVersion: number): Promise<void> {
    await api.delete(`/graph/relations/${relationId}`, {
      params: { expected_version: expectedVersion },
    });
  },

  /**
   * Generate Mermaid diagram.
   */
  async generateMermaid(params: {
    document_id?: string;
    topic?: string;
    max_nodes?: number;
    max_depth?: number;
    format?: string;
  }): Promise<{ mermaid_code: string; metadata: any }> {
    const response = await api.post('/graph/mermaid', params);
    return response.data;
  },
};
