import { create } from 'zustand';
import { Node, Edge } from 'reactflow';

// ============================================================================
// Types
// ============================================================================

export interface GraphNode extends Node {
  id: string;
  label: string;
  type: string;
  description?: string;
  confidence?: number;
  version?: number;
  entityId?: string; // DB UUID
}

export interface GraphEdge extends Edge {
  id: string;
  source: string;
  target: string;
  label: string;
  relationType: string;
  version?: number;
  relationId?: string; // DB UUID
}

interface GraphHistory {
  past: Array<{ nodes: GraphNode[]; edges: GraphEdge[] }>;
  future: Array<{ nodes: GraphNode[]; edges: GraphEdge[] }>;
}

// ============================================================================
// Store Interface
// ============================================================================

interface GraphState {
  // Data
  nodes: GraphNode[];
  edges: GraphEdge[];
  documentId: string | null;
  selectedId: string | null;
  isLoading: boolean;

  // History (Undo/Redo)
  history: GraphHistory;

  // Actions — Data
  setNodes: (nodes: GraphNode[]) => void;
  setEdges: (edges: GraphEdge[]) => void;
  setDocumentId: (id: string | null) => void;
  setSelectedId: (id: string | null) => void;
  setLoading: (loading: boolean) => void;

  // Actions — CRUD (with history tracking)
  addNode: (node: GraphNode) => void;
  updateNode: (id: string, updates: Partial<GraphNode>) => void;
  deleteNode: (id: string) => void;
  addEdge: (edge: GraphEdge) => void;
  deleteEdge: (id: string) => void;

  // Actions — History
  undo: () => void;
  redo: () => void;
  canUndo: () => boolean;
  canRedo: () => boolean;
  pushHistory: () => void;

  // Actions — Reset
  reset: () => void;
}

const MAX_HISTORY = 50;

// ============================================================================
// Store
// ============================================================================

export const useGraphStore = create<GraphState>((set, get) => ({
  // Initial state
  nodes: [],
  edges: [],
  documentId: null,
  selectedId: null,
  isLoading: false,
  history: { past: [], future: [] },

  // Data actions
  setNodes: (nodes) => set({ nodes }),
  setEdges: (edges) => set({ edges }),
  setDocumentId: (documentId) => set({ documentId }),
  setSelectedId: (selectedId) => set({ selectedId }),
  setLoading: (isLoading) => set({ isLoading }),

  // Push current state to history
  pushHistory: () => {
    const { nodes, edges, history } = get();
    set({
      history: {
        past: [...history.past.slice(-(MAX_HISTORY - 1)), { nodes, edges }],
        future: [], // Clear future on new action
      },
    });
  },

  // CRUD actions with history
  addNode: (node) => {
    get().pushHistory();
    set((state) => ({ nodes: [...state.nodes, node] }));
  },

  updateNode: (id, updates) => {
    get().pushHistory();
    set((state) => ({
      nodes: state.nodes.map((n) => (n.id === id ? { ...n, ...updates } : n)),
    }));
  },

  deleteNode: (id) => {
    get().pushHistory();
    set((state) => ({
      nodes: state.nodes.filter((n) => n.id !== id),
      edges: state.edges.filter(
        (e) => e.source !== id && e.target !== id
      ),
      selectedId: state.selectedId === id ? null : state.selectedId,
    }));
  },

  addEdge: (edge) => {
    get().pushHistory();
    set((state) => ({ edges: [...state.edges, edge] }));
  },

  deleteEdge: (id) => {
    get().pushHistory();
    set((state) => ({
      edges: state.edges.filter((e) => e.id !== id),
    }));
  },

  // History actions
  undo: () => {
    const { history, nodes, edges } = get();
    if (history.past.length === 0) return;

    const previous = history.past[history.past.length - 1];
    set({
      nodes: previous.nodes,
      edges: previous.edges,
      history: {
        past: history.past.slice(0, -1),
        future: [{ nodes, edges }, ...history.future],
      },
    });
  },

  redo: () => {
    const { history, nodes, edges } = get();
    if (history.future.length === 0) return;

    const next = history.future[0];
    set({
      nodes: next.nodes,
      edges: next.edges,
      history: {
        past: [...history.past, { nodes, edges }],
        future: history.future.slice(1),
      },
    });
  },

  canUndo: () => get().history.past.length > 0,
  canRedo: () => get().history.future.length > 0,

  // Reset
  reset: () =>
    set({
      nodes: [],
      edges: [],
      documentId: null,
      selectedId: null,
      isLoading: false,
      history: { past: [], future: [] },
    }),
}));
