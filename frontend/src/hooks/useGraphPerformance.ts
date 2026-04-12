import { useState, useEffect, useRef, useCallback, useMemo } from 'react';

// ─── Types ─────────────────────────────────────────────────────
export interface GraphNode {
  id: string;
  x?: number;
  y?: number;
  [key: string]: any;
}

export interface GraphEdge {
  id?: string;
  source: string | GraphNode;
  target: string | GraphNode;
  [key: string]: any;
}

export interface Viewport {
  width: number;
  height: number;
  offsetX: number;
  offsetY: number;
  zoom: number;
}

export interface UseGraphPerformanceOptions {
  nodes: GraphNode[];
  edges: GraphEdge[];
  viewport: Viewport;
  /** Buffer zone in pixels around viewport edges */
  bufferZone?: number;
  /** Zoom threshold below which nearby nodes are clustered */
  clusterZoomThreshold?: number;
  /** Max pixel distance for clustering */
  clusterDistance?: number;
  /** Debounce delay in ms for zoom/pan events */
  debounceMs?: number;
}

export interface UseGraphPerformanceReturn {
  /** Nodes filtered to visible + buffered area (clustered if zoomed out) */
  visibleNodes: GraphNode[];
  /** Edges connecting visible nodes */
  visibleEdges: GraphEdge[];
  /** All nodes (unfiltered) for reference */
  allNodes: GraphNode[];
  /** Current debounced zoom level */
  zoom: number;
  /** IntersectionObserver visibility state */
  isGraphVisible: boolean;
  /** Ref to attach IntersectionObserver to the graph container */
  containerRef: (el: HTMLElement | null) => void;
  /** Debounced viewport update (call on zoom/pan) */
  updateViewport: (vp: Partial<Viewport>) => void;
}

// ─── Helpers ───────────────────────────────────────────────────
function debounce<T extends (...args: any[]) => void>(fn: T, ms: number): T {
  let timer: ReturnType<typeof setTimeout> | null = null;
  return ((...args: any[]) => {
    if (timer) clearTimeout(timer);
    timer = setTimeout(() => fn(...args), ms);
  }) as T;
}

function getNodeId(source: string | GraphNode): string {
  return typeof source === 'string' ? source : source.id;
}

function isInViewport(
  node: GraphNode,
  vp: Viewport,
  buffer: number,
): boolean {
  if (node.x == null || node.y == null) return true;
  const left = -vp.offsetX / vp.zoom - buffer;
  const right = (-vp.offsetX + vp.width) / vp.zoom + buffer;
  const top = -vp.offsetY / vp.zoom - buffer;
  const bottom = (-vp.offsetY + vp.height) / vp.zoom + buffer;
  return node.x >= left && node.x <= right && node.y >= top && node.y <= bottom;
}

function clusterNodes(
  nodes: GraphNode[],
  edges: GraphEdge[],
  distance: number,
): GraphNode[] {
  const visited = new Set<string>();
  const clusters: GraphNode[] = [];
  const nodeMap = new Map(nodes.map((n) => [n.id, n]));

  for (const node of nodes) {
    if (visited.has(node.id)) continue;
    visited.add(node.id);

    const cluster: GraphNode[] = [node];
    for (const other of nodes) {
      if (visited.has(other.id) || other.id === node.id) continue;
      const dx = (other.x ?? 0) - (node.x ?? 0);
      const dy = (other.y ?? 0) - (node.y ?? 0);
      if (Math.sqrt(dx * dx + dy * dy) <= distance) {
        visited.add(other.id);
        cluster.push(other);
      }
    }

    if (cluster.length > 1) {
      clusters.push({
        ...node,
        id: `cluster_${node.id}`,
        _clusterSize: cluster.length,
        _clusterIds: cluster.map((c) => c.id),
        x: cluster.reduce((s, c) => s + (c.x ?? 0), 0) / cluster.length,
        y: cluster.reduce((s, c) => s + (c.y ?? 0), 0) / cluster.length,
      });
    } else {
      clusters.push(node);
    }
  }

  return clusters;
}

// ─── Hook ──────────────────────────────────────────────────────
export default function useGraphPerformance({
  nodes,
  edges,
  viewport,
  bufferZone = 80,
  clusterZoomThreshold = 0.6,
  clusterDistance = 60,
  debounceMs = 100,
}: UseGraphPerformanceOptions): UseGraphPerformanceReturn {
  const [debouncedVp, setDebouncedVp] = useState<Viewport>(viewport);
  const [isGraphVisible, setIsGraphVisible] = useState(true);

  // IntersectionObserver ref
  const containerEl = useRef<HTMLElement | null>(null);
  const observerRef = useRef<IntersectionObserver | null>(null);

  const containerRef = useCallback((el: HTMLElement | null) => {
    containerEl.current = el;
    if (observerRef.current) observerRef.current.disconnect();
    if (el) {
      observerRef.current = new IntersectionObserver(
        ([entry]) => setIsGraphVisible(entry.isIntersecting),
        { threshold: 0.01 },
      );
      observerRef.current.observe(el);
    }
  }, []);

  // Debounced viewport updates
  const debouncedUpdate = useRef(
    debounce((vp: Viewport) => setDebouncedVp(vp), debounceMs),
  ).current;

  const updateViewport = useCallback(
    (partial: Partial<Viewport>) => {
      const next = { ...debouncedVp, ...partial };
      debouncedUpdate(next);
    },
    [debouncedVp, debouncedUpdate],
  );

  useEffect(() => {
    return () => {
      observerRef.current?.disconnect();
    };
  }, []);

  // Filter visible nodes
  const visibleNodes = useMemo(() => {
    if (!isGraphVisible) return [];
    const filtered = nodes.filter((n) => isInViewport(n, debouncedVp, bufferZone));
    if (debouncedVp.zoom < clusterZoomThreshold) {
      return clusterNodes(filtered, edges, clusterDistance);
    }
    return filtered;
  }, [nodes, edges, debouncedVp, bufferZone, clusterZoomThreshold, clusterDistance, isGraphVisible]);

  // Filter edges connecting visible nodes
  const visibleEdges = useMemo(() => {
    if (!isGraphVisible) return [];
    const visibleIds = new Set(visibleNodes.flatMap((n) => (n as any)._clusterIds ?? [n.id]));
    return edges.filter((e) => {
      const s = getNodeId(e.source);
      const t = getNodeId(e.target);
      return visibleIds.has(s) && visibleIds.has(t);
    });
  }, [edges, visibleNodes, isGraphVisible]);

  return {
    visibleNodes,
    visibleEdges,
    allNodes: nodes,
    zoom: debouncedVp.zoom,
    isGraphVisible,
    containerRef,
    updateViewport,
  };
}
