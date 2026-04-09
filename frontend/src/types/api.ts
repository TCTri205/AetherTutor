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

// ============================================
// STAGE 2: Flashcards (SM-2 Spaced Repetition)
// ============================================

export type FlashcardSource = 'manual' | 'quiz_wrong_answer' | 'auto_generated';

export interface FlashcardRead {
  id: string;
  user_id: string;
  document_id: string | null;
  front: string;
  back: string;
  source: FlashcardSource;
  metadata: Record<string, any>;
  sm2_ease_factor: number;
  sm2_interval: number;
  sm2_repetitions: number;
  sm2_next_review: string;
  created_at: string;
  updated_at: string;
}

export interface FlashcardCreate {
  front: string;
  back: string;
  source?: FlashcardSource;
  metadata?: Record<string, any>;
  document_id?: string;
}

export interface FlashcardUpdate {
  front?: string;
  back?: string;
}

export interface FlashcardDueResponse {
  cards: FlashcardRead[];
  total_due: number;
}

export interface FlashcardReviewRequest {
  card_id: string;
  quality: number; // 0=Again, 2=Hard, 3=Good, 5=Easy
  idempotency_key?: string;
  time_taken_ms?: number;
}

export interface FlashcardReviewResponse {
  success: boolean;
  message: string;
  card_id: string;
  ease_factor: number;
  interval: number;
  repetitions: number;
  next_review: string;
}

export interface FlashcardStatsResponse {
  total_cards: number;
  due_cards: number;
  total_reviews: number;
  avg_quality: number;
  streak_days: number;
  total_reviews_7d: number;
}

export interface FlashcardBulkGenerateRequest {
  document_id: string;
  source?: FlashcardSource;
}

export interface FlashcardBulkGenerateResponse {
  success: boolean;
  cards_created: number;
  cards: FlashcardRead[];
}

// ============================================
// STAGE 2: Quiz (Examiner Agent)
// ============================================

export type QuizQuestionType = 'multiple_choice' | 'true_false';
export type QuizDifficulty = 1 | 2 | 3 | 4 | 5;

export interface QuizGenerateRequest {
  document_id?: string;
  topic?: string;
  num_questions?: number;
  question_types?: QuizQuestionType[];
  difficulty?: QuizDifficulty;
}

export interface QuizQuestionResponse {
  question_id: string;
  order: number;
  entity_name: string;
  question_text: string;
  question_type: QuizQuestionType;
  difficulty: number;
  bloom_level: string;
  options?: string[];
}

export interface QuizResponse {
  id: string;
  user_id: string;
  document_id: string | null;
  title: string;
  description: string | null;
  topic: string | null;
  num_questions: number;
  question_types: string[];
  difficulty: number;
  questions: QuizQuestionResponse[];
  created_at: string;
}

export interface QuizListItemResponse {
  id: string;
  title: string;
  topic: string | null;
  num_questions: number;
  difficulty: number;
  created_at: string;
}

export interface QuizSubmitRequest {
  answers: Array<{
    question_id: string;
    answer: string;
  }>;
}

export interface QuizAnswerResponse {
  question_id: string;
  question_text: string;
  question_type: QuizQuestionType;
  user_answer: string;
  correct_answer: string;
  is_correct: boolean;
  explanation?: string;
  entity_name?: string;
  bloom_level: string;
  difficulty: number;
}

export interface WeakAreaResponse {
  entity_name: string;
  entity_type: string;
  bloom_level: string;
}

export interface QuizResultResponse {
  id: string;
  quiz_id: string;
  score: number;
  correct_count: number;
  wrong_count: number;
  total_questions: number;
  results: QuizAnswerResponse[];
  weak_areas: WeakAreaResponse[];
  completed_at: string;
}

export interface QuizStatsResponse {
  total_quizzes: number;
  average_score: number;
  total_questions_answered: number;
  total_correct: number;
  overall_accuracy: number;
}

export interface WeakAreasResponse {
  entity_name: string;
  wrong_count: number;
  avg_difficulty: number;
}

export interface QuizResultListItemResponse {
  id: string;
  quiz_id: string;
  quiz_title: string;
  score: number;
  correct_answers: number;
  total_questions: number;
  completed_at: string;
}

export interface FlashcardSuggestionResponse {
  front: string;
  back: string;
  metadata: Record<string, any>;
}

export interface QuizFeedbackRequest {
  quality_rating: number; // 1-5
  quality_feedback?: string;
}

// ============================================
// STAGE 2: Zettelkasten (Notes & Backlinks)
// ============================================

export type NoteType = 'fleeting' | 'literature' | 'permanent' | 'project';
export type NoteLinkType = 'manual' | 'ai_suggested' | 'confirmed';

export interface NoteCreate {
  title: string;
  content: string;
  note_type?: NoteType;
  tags?: string[];
  metadata?: Record<string, any>;
}

export interface NoteRead {
  id: string;
  user_id: string;
  title: string;
  content: string;
  note_type: string;
  tags: string[];
  metadata: Record<string, any>;
  created_at: string;
  updated_at: string;
}

export interface NoteLinkInfo {
  id: string;
  source_note_id: string;
  target_note_id: string;
  context: string | null;
  link_type: NoteLinkType;
  created_at: string;
}

export interface NoteDetail extends NoteRead {
  outgoing_links: NoteLinkInfo[];
  incoming_links: NoteLinkInfo[];
}

export interface NoteListItem {
  id: string;
  title: string;
  note_type: string;
  tags: string[];
  created_at: string;
  updated_at: string;
}

export interface NoteListResponse {
  notes: NoteListItem[];
  total: number;
}

export interface NoteUpdate {
  title?: string;
  content?: string;
  tags?: string[];
  note_type?: string;
}

export interface NoteLinkCreate {
  target_note_id: string;
  context?: string;
}

export interface NoteLinkResponse {
  id: string;
  source_note_id: string;
  target_note_id: string;
  context: string | null;
  link_type: NoteLinkType;
  created_at: string;
}

export interface RelatedEntitySuggestion {
  entity_name: string;
  relation_type: string;
  confidence: number;
  context: string;
}

export interface RelatedNoteSuggestion {
  note_id: string;
  note_title: string;
  relation_type: string;
  confidence: number;
  context: string;
}

export interface BacklinkSuggestionsResponse {
  related_entities: RelatedEntitySuggestion[];
  related_notes: RelatedNoteSuggestion[];
}

export interface NoteGraphNode {
  id: string;
  title: string;
  note_type: string;
  tags: string[];
  created_at: string;
}

export interface NoteGraphEdge {
  source: string;
  target: string;
  link_type: string;
  context: string | null;
}

export interface NoteGraphResponse {
  nodes: NoteGraphNode[];
  edges: NoteGraphEdge[];
}
