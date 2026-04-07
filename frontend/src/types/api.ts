export type DocumentStatus = 'PENDING' | 'PROCESSING' | 'COMPLETED' | 'FAILED';

export type ProcessingStep = 
  | 'INITIAL'
  | 'QUEUED'
  | 'EXTRACTING'
  | 'CHUNKING'
  | 'EXTRACTING_ENTITIES'
  | 'BUILDING_GRAPH'
  | 'EMBEDDING'
  | 'COMPLETED'
  | 'FAILED';

export interface DocumentDetail {
  id: string;
  filename: string;
  status: DocumentStatus;
  processing_step: ProcessingStep;
  entity_count: number;
  relation_count: number;
  page_count: number | null;
  file_size: number | null;
  created_at: string;
  updated_at: string;
  error_message: string | null;
}

export interface DocumentUploadResponse {
  document_id: string;
  filename: string;
  status: DocumentStatus;
  message: string;
}

export interface QueryRequest {
  query: string;
  document_id?: string;
}

export interface QueryResponse {
  query: string;
  response: string;
  context_used: any[];
}

export interface GraphNodeView {
  id: string;
  label: string;
  type: string;
  description: string;
}

export interface GraphEdgeView {
  id: string;
  source: string;
  target: string;
  label: string;
  description: string;
}

export interface GraphData {
  nodes: GraphNodeView[];
  edges: GraphEdgeView[];
}

export interface GraphStats {
  entity_count: number;
  relation_count: number;
}

export interface ConversationRead {
  id: string;
  document_id: string;
  title: string;
  created_at: string;
  last_message_at: string;
}

export interface MessageRead {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  reasoning?: string;
  status: 'PENDING' | 'COMPLETED' | 'FAILED';
  created_at: string;
  context_used?: any;
}

export interface ConversationDetail extends ConversationRead {
  messages: MessageRead[];
}
