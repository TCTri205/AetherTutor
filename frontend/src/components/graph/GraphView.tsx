import { useState, useCallback, useRef, useEffect, forwardRef, useImperativeHandle } from 'react';
import ForceGraph2D, { type ForceGraphMethods } from 'react-force-graph-2d';

// ─── Constants ─────────────────────────────────────────────────
const communityColors = [
  '#6366f1', '#f59e0b', '#10b981', '#a855f7', '#ec4899',
  '#3b82f6', '#f97316', '#06b6d4', '#8b5cf6', '#f43f5e',
  '#84cc16', '#eab308'
];

const typeColors: Record<string, string> = {
  concept: '#6366f1',
  term: '#f59e0b',
  process: '#10b981',
  theory: '#a855f7',
};

const DEFAULT_COLOR_HEX = '#94a3b8';

const relationColors: Record<string, string> = {
  explains: '#10b981',
  contradicts: '#ef4444',
  supports: '#3b82f6',
  defines: '#6366f1',
  mentions: '#94a3b8',
  'related to': '#94a3b8',
};

// ─── Props Interface ───────────────────────────────────────────
export interface GraphViewProps {
  data: { nodes: any[]; links: any[] };
  onNodeClick: (node: any) => void;
  isLoading?: boolean;
  searchQuery?: string;
  selectedTag?: string | null;
  showObsidianBadges?: boolean;
  autoFit?: boolean;
  width?: number;
  height?: number;
  onNodeDragEnd?: (node: any) => void;
}

export interface GraphViewRef {
  zoomToFit: (duration?: number, padding?: number) => void;
}

// ─── GraphView Component ───────────────────────────────────────
const GraphView = forwardRef<GraphViewRef, GraphViewProps>((props, ref) => {
  const {
    data,
    onNodeClick,
    isLoading = false,
    searchQuery = '',
    selectedTag = null,
    showObsidianBadges = true,
    autoFit = true,
    width,
    height,
    onNodeDragEnd,
  } = props;

  const fgRef = useRef<ForceGraphMethods>(null as any);

  // Expose zoomToFit via ref
  useImperativeHandle(ref, () => ({
    zoomToFit: (duration = 400, padding = 100) => {
      fgRef.current?.zoomToFit(duration, padding);
    },
  }), []);

  // Interaction state
  const hoverNodeRef = useRef<any>(null);
  const highlightNodesRef = useRef<Set<string>>(new Set());
  const highlightLinksRef = useRef<Set<string>>(new Set());

  // Auto-fit after data loads
  useEffect(() => {
    if (autoFit && data.nodes.length > 0) {
      const timer = setTimeout(() => {
        fgRef.current?.zoomToFit(400, 100);
      }, 500);
      return () => clearTimeout(timer);
    }
  }, [data.nodes.length, autoFit]);

  // Highlight management
  const updateHighlight = useCallback(() => {
    // Force re-render by triggering state update
    setHighlightVersion(v => v + 1);
  }, []);

  const [highlightVersion, setHighlightVersion] = useState(0);

  const handleNodeHover = useCallback((node: any) => {
    highlightNodesRef.current.clear();
    highlightLinksRef.current.clear();
    if (node) {
      highlightNodesRef.current.add(node.id);
      data.links.forEach((link: any) => {
        if (link.source.id === node.id || link.target.id === node.id) {
          highlightLinksRef.current.add(link.id);
          highlightNodesRef.current.add(link.source.id);
          highlightNodesRef.current.add(link.target.id);
        }
      });
    }
    hoverNodeRef.current = node || null;
    updateHighlight();
  }, [data.links, updateHighlight]);

  const handleLinkHover = useCallback((link: any) => {
    highlightNodesRef.current.clear();
    highlightLinksRef.current.clear();
    if (link) {
      highlightLinksRef.current.add(link.id);
      highlightNodesRef.current.add(link.source.id);
      highlightNodesRef.current.add(link.target.id);
    }
    updateHighlight();
  }, [updateHighlight]);

  // Canvas Custom Rendering - paintNode
  const paintNode = useCallback((node: any, ctx: CanvasRenderingContext2D, globalScale: number) => {
    const highlightNodes = highlightNodesRef.current;
    const hoverNode = hoverNodeRef.current;

    const isHighlighted = highlightNodes.size === 0 || highlightNodes.has(node.id);
    const isSearchMatch = !searchQuery || node.name.toLowerCase().includes(searchQuery.toLowerCase());
    const isTagMatch = !selectedTag || (node.tags && node.tags.includes(selectedTag));
    const opacity = (isHighlighted && isSearchMatch && isTagMatch) ? 1 : 0.05;

    // Choose color: Priority Community > Type > Default
    let nodeColor = DEFAULT_COLOR_HEX;
    if (node.community !== undefined && node.community !== null) {
      nodeColor = communityColors[node.community % communityColors.length];
    } else {
      nodeColor = typeColors[node.type?.toLowerCase()] || DEFAULT_COLOR_HEX;
    }

    const label = node.name;
    const fontSize = 12 / globalScale;

    // Draw outer glow if hovered or searched
    if (hoverNode?.id === node.id || (searchQuery && isSearchMatch)) {
      ctx.shadowBlur = 15;
      ctx.shadowColor = nodeColor;
    }

    // Draw node circle
    ctx.beginPath();
    ctx.arc(node.x!, node.y!, node.val, 0, 2 * Math.PI, false);
    ctx.fillStyle = nodeColor;
    ctx.globalAlpha = opacity;
    ctx.fill();

    // Reset shadow
    ctx.shadowBlur = 0;

    // Draw border
    ctx.lineWidth = 2 / globalScale;
    ctx.strokeStyle = '#ffffff';
    ctx.stroke();

    // Source Indicator (Badge)
    if (showObsidianBadges && node.source === 'obsidian_import' && opacity > 0.5) {
      const badgeSize = node.val * 0.6;
      ctx.fillStyle = '#a855f7'; // Purple for Obsidian
      ctx.beginPath();
      ctx.arc(node.x! + node.val * 0.7, node.y! - node.val * 0.7, badgeSize / 2, 0, 2 * Math.PI);
      ctx.fill();
      ctx.strokeStyle = '#fff';
      ctx.lineWidth = 1 / globalScale;
      ctx.stroke();

      // Draw 'O' letter
      ctx.font = `bold ${badgeSize * 0.8}px Inter`;
      ctx.fillStyle = '#fff';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillText('O', node.x! + node.val * 0.7, node.y! - node.val * 0.7);
    }

    // Tag badges
    if (node.tags && node.tags.length > 0 && opacity > 0.5 && globalScale > 2) {
      const tagCount = Math.min(node.tags.length, 3); // Max 3 badges
      for (let i = 0; i < tagCount; i++) {
        const tagBadgeSize = node.val * 0.4;
        const angle = (Math.PI / 2) + (i * 0.4) - 0.4;
        const badgeX = node.x! + Math.cos(angle) * (node.val + tagBadgeSize + 2);
        const badgeY = node.y! + Math.sin(angle) * (node.val + tagBadgeSize + 2);

        ctx.fillStyle = '#06b6d4'; // Cyan for tags
        ctx.beginPath();
        ctx.arc(badgeX, badgeY, tagBadgeSize / 2, 0, 2 * Math.PI);
        ctx.fill();
      }
    }

    // Draw Label if zoomed in or highlighted
    if (globalScale > 1.5 || isHighlighted || node === hoverNode) {
      ctx.font = `${fontSize}px Inter, sans-serif`;
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillStyle = `rgba(255, 255, 255, ${opacity})`;
      ctx.fillText(label, node.x!, node.y! + node.val + fontSize + 2);
    }

    ctx.globalAlpha = 1;
  }, [searchQuery, selectedTag, showObsidianBadges]);

  // Canvas Custom Rendering - paintLink
  const paintLink = useCallback((link: any, ctx: CanvasRenderingContext2D, globalScale: number) => {
    const highlightLinks = highlightLinksRef.current;
    const hoverNode = hoverNodeRef.current;

    const isHighlighted = highlightLinks.size === 0 || highlightLinks.has(link.id);

    // Choose color based on relation type
    const linkColor = relationColors[link.label?.toLowerCase()] || '#94a3b8';

    // Edge line
    ctx.strokeStyle = isHighlighted ? linkColor : `rgba(148, 163, 184, 0.6)`;
    ctx.lineWidth = (isHighlighted ? 2 : 1) / globalScale;
    ctx.beginPath();
    ctx.moveTo(link.source.x!, link.source.y!);
    ctx.lineTo(link.target.x!, link.target.y!);
    ctx.stroke();

    // Label if highlighted and zoom is enough OR if very close
    if (isHighlighted && (globalScale > 2.5 || (hoverNode && (link.source.id === hoverNode.id || link.target.id === hoverNode.id))) && link.label) {
      const midX = (link.source.x! + link.target.x!) / 2;
      const midY = (link.source.y! + link.target.y!) / 2;
      const fontSize = 10 / globalScale;

      ctx.save();
      ctx.font = `italic ${fontSize}px Inter, sans-serif`;
      ctx.textAlign = 'center';

      // Draw small background for label
      const textWidth = ctx.measureText(link.label).width;
      ctx.fillStyle = 'rgba(2, 6, 23, 0.9)';
      ctx.fillRect(midX - textWidth/2 - 2, midY - fontSize/2 - 2, textWidth + 4, fontSize + 4);

      ctx.fillStyle = linkColor;
      ctx.fillText(link.label, midX, midY);
      ctx.restore();
    }
  }, []);

  // Expose fgRef via a callback for parent components to access
  const graphContainerRef = useCallback((div: HTMLDivElement | null) => {
    if (div && !div.dataset.initialized) {
      div.dataset.initialized = 'true';
    }
  }, []);

  return (
    <div ref={graphContainerRef} className="w-full h-full" style={width && height ? { width, height } : undefined}>
      <ForceGraph2D
        ref={fgRef}
        graphData={data}
        backgroundColor="#020617"
        nodeCanvasObject={paintNode}
        linkCanvasObject={paintLink}
        nodePointerAreaPaint={(node, color, ctx) => {
          ctx.fillStyle = color;
          ctx.beginPath();
          ctx.arc(node.x!, node.y!, node.val + 2, 0, 2 * Math.PI, false);
          ctx.fill();
        }}
        onNodeHover={handleNodeHover}
        onLinkHover={handleLinkHover}
        onNodeClick={onNodeClick}
        onNodeDragEnd={onNodeDragEnd}
        cooldownTicks={100}
        d3AlphaDecay={0.02}
        d3VelocityDecay={0.3}
        linkDirectionalParticles={(link: any) => highlightLinksRef.current.has(link.id) ? 2 : 0}
        linkDirectionalParticleSpeed={0.01}
        enableNodeDrag={true}
      />
    </div>
  );
});

GraphView.displayName = 'GraphView';

export default GraphView;

// Re-export ForceGraphMethods for parent components
export type { ForceGraphMethods };
