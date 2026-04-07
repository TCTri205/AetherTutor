import { useEffect, useState, useCallback, useMemo, useRef } from 'react';
import ReactFlow, {
  Background,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
  type Node,
  type Edge,
  MarkerType,
  Position,
} from 'reactflow';
import 'reactflow/dist/style.css';
import { useParams, useLocation } from 'react-router-dom';
import { graphService } from '../services/graph';
import {
  Network,
  RefreshCcw,
  Maximize2,
  Search,
  Filter,
  Zap,
  MousePointer2,
  Loader2,
  Share2,
  MessageSquare,
  X,
  Hash,
} from 'lucide-react';
import { Button } from '../components/ui/Button';
import { Card } from '../components/ui/Card';
import GraphSidebar from '../components/graph/GraphSidebar';
import { cn } from '../lib/utils';
import { toast } from 'sonner';

// ─── Custom Node ───────────────────────────────────────────────
const typeColors: Record<string, { bg: string; border: string; text: string; icon: string }> = {
  concept: { bg: 'bg-indigo-500/20', border: 'border-indigo-500/40', text: 'text-indigo-400', icon: 'text-indigo-400' },
  term: { bg: 'bg-amber-500/20', border: 'border-amber-500/40', text: 'text-amber-400', icon: 'text-amber-400' },
  process: { bg: 'bg-emerald-500/20', border: 'border-emerald-500/40', text: 'text-emerald-400', icon: 'text-emerald-400' },
  theory: { bg: 'bg-purple-500/20', border: 'border-purple-500/40', text: 'text-purple-400', icon: 'text-purple-400' },
};

const typeIcons: Record<string, any> = {
  concept: Zap,
  term: Hash,
  process: Share2,
  theory: MessageSquare,
};

const EntityNode = ({ data }: any) => {
  const colors = typeColors[data.nodeType?.toLowerCase()] || typeColors.concept;
  const Icon = typeIcons[data.nodeType?.toLowerCase()] || Zap;

  return (
    <div className={cn(
      "px-4 py-3 rounded-2xl bg-black/80 backdrop-blur-xl border shadow-2xl flex flex-col items-center gap-1 min-w-[120px] transition-all hover:scale-105",
      colors.border,
      data.isDimmed && "opacity-30"
    )}>
      <div className={cn("w-8 h-8 rounded-xl flex items-center justify-center mb-1", colors.bg)}>
        <Icon className={cn("w-4 h-4", colors.icon)} />
      </div>
      <span className="text-white font-bold text-sm tracking-tight text-center">{data.label}</span>
      <span className={cn("text-[10px] uppercase font-bold tracking-widest", colors.text)}>
        {data.nodeType || 'Entity'}
      </span>
    </div>
  );
};

const nodeTypes = { entity: EntityNode };

// ─── Custom Edge với label ─────────────────────────────────────
const GraphEdge = ({ id, sourceX, sourceY, targetX, targetY, label, style, data }: any) => {
  const midX = (sourceX + targetX) / 2;
  const midY = (sourceY + targetY) / 2;

  return (
    <g>
      <path
        d={`M${sourceX},${sourceY} C${midX},${sourceY} ${midX},${targetY} ${targetX},${targetY}`}
        fill="none"
        stroke={style?.stroke || '#475569'}
        strokeWidth={style?.strokeWidth || 2}
        markerEnd="url(#arrow)"
        className="transition-all duration-200"
      />
      {label && (
        <g>
          <rect
            x={midX - 40}
            y={midY - 10}
            width={80}
            height={20}
            rx={4}
            fill="#0f172a"
            stroke="#334155"
            strokeWidth={1}
          />
          <text
            x={midX}
            y={midY + 4}
            textAnchor="middle"
            fill="#94a3b8"
            fontSize={9}
            fontWeight="600"
          >
            {label.length > 15 ? label.slice(0, 15) + '...' : label}
          </text>
        </g>
      )}
    </g>
  );
};

const edgeTypes = { graphEdge: GraphEdge };

// ─── Radial Layout Helper ──────────────────────────────────────
function calculateRadialLayout(nodesCount: number, centerX: number, centerY: number, radius: number) {
  if (nodesCount === 0) return [];
  if (nodesCount === 1) return [{ x: centerX, y: centerY }];

  const positions: { x: number; y: number }[] = [];
  for (let i = 0; i < nodesCount; i++) {
    const angle = (2 * Math.PI * i) / nodesCount - Math.PI / 2; // Start from top
    positions.push({
      x: centerX + radius * Math.cos(angle),
      y: centerY + radius * Math.sin(angle),
    });
  }
  return positions;
}

// ─── Main Component ────────────────────────────────────────────
export default function GraphExplorer() {
  const { documentId } = useParams<{ documentId: string }>();
  const location = useLocation();
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [hasData, setHasData] = useState(false);

  // Search & filter
  const [searchQuery, setSearchQuery] = useState('');
  const [searchOpen, setSearchOpen] = useState(false);
  const [selectedEntity, setSelectedEntity] = useState<any>(null);
  const [sidebarOpen, setSidebarOpen] = useState(false);

  // Highlight entity from navigation state (from ContextChips click)
  const highlightEntity = location.state?.highlightEntity as string | undefined;

  // Fetch graph data
  const fetchGraphData = useCallback(async () => {
    if (!documentId) return;
    setIsLoading(true);
    try {
      const data = await graphService.getDocumentGraph(documentId!);

      if (!data.nodes || data.nodes.length === 0) {
        setHasData(false);
        setNodes([]);
        setEdges([]);
        setIsLoading(false);
        return;
      }

      setHasData(true);

      // S7.3: Radial layout thay vì random
      const positions = calculateRadialLayout(data.nodes.length, 400, 300, 250);

      const newNodes: Node[] = data.nodes.map((node: any, index: number) => ({
        id: node.id,
        type: 'entity',
        data: {
          label: node.label || node.id,
          nodeType: node.type || 'concept',
          description: node.description,
          isDimmed: false,
        },
        position: positions[index] || { x: Math.random() * 800, y: Math.random() * 600 },
        sourcePosition: Position.Right,
        targetPosition: Position.Left,
      }));

      // S7.2: Custom edges với relation_type label
      const newEdges: Edge[] = data.edges.map((edge: any) => ({
        id: `${edge.source}-${edge.target}`,
        source: edge.source,
        target: edge.target,
        type: 'graphEdge',
        data: {
          label: edge.relation_type || edge.label || '',
          description: edge.description,
        },
        label: edge.relation_type || edge.label || '',
        animated: true,
        style: { stroke: '#475569', strokeWidth: 2 },
        markerEnd: { type: MarkerType.ArrowClosed, color: '#475569' },
      }));

      setNodes(newNodes);
      setEdges(newEdges);

      // Highlight entity nếu có từ navigation
      if (highlightEntity) {
        const targetNode = newNodes.find(n => n.data.label === highlightEntity);
        if (targetNode) {
          setSelectedEntity({
            id: targetNode.id,
            label: targetNode.data.label,
            type: targetNode.data.nodeType,
            description: targetNode.data.description,
            neighbors: newEdges
              .filter(e => e.source === targetNode.id || e.target === targetNode.id)
              .map(e => ({
                target: e.source === targetNode.id ? e.target : e.source,
                relation_type: e.data?.label || '',
                description: e.data?.description,
              })),
            degree: newEdges.filter(e => e.source === targetNode.id || e.target === targetNode.id).length,
          });
          setSidebarOpen(true);
        }
      }
    } catch (err: any) {
      toast.error(`Lỗi tải đồ thị: ${err.message}`);
    } finally {
      setIsLoading(false);
    }
  }, [documentId, highlightEntity, setNodes, setEdges]);

  useEffect(() => {
    fetchGraphData();
  }, [fetchGraphData]);

  // S7.4: Search filtering
  const filteredNodes = useMemo(() => {
    if (!searchQuery.trim()) return nodes;

    const query = searchQuery.toLowerCase();
    return nodes.map(node => ({
      ...node,
      data: {
        ...node.data,
        isDimmed: !node.data.label.toLowerCase().includes(query),
      },
    }));
  }, [nodes, searchQuery]);

  // Node click → open sidebar
  const onNodeClick = useCallback((_event: React.MouseEvent, node: Node) => {
    const entityData = {
      id: node.id,
      label: node.data.label,
      type: node.data.nodeType,
      description: node.data.description,
      neighbors: edges
        .filter(e => e.source === node.id || e.target === node.id)
        .map(e => ({
          target: e.source === node.id ? e.target : e.source,
          relation_type: e.data?.label || '',
          description: e.data?.description,
        })),
      degree: edges.filter(e => e.source === node.id || e.target === node.id).length,
    };

    setSelectedEntity(entityData);
    setSidebarOpen(true);
  }, [edges]);

  // Fit view button
  const reactFlowWrapper = useRef<any>(null);
  const handleFitView = () => {
    // React Flow's fitView is handled by the Controls component
    window.dispatchEvent(new CustomEvent('reactflow-fitview'));
  };

  return (
    <div className="flex h-full overflow-hidden bg-[#020617] rounded-3xl border border-white/5 relative">
      {/* Main Graph Area */}
      <div className="flex-1 relative">
        {/* Header Overlay */}
        <div className="absolute top-6 left-6 z-10 flex items-center gap-4">
          <Card className="glass px-6 py-4 border-white/10 shadow-2xl flex items-center gap-6">
            <div className="flex items-center gap-3 pr-6 border-r border-white/10 font-bold text-white tracking-tight">
              <Network className="w-5 h-5 text-primary" />
              Bản Đồ Tri Thức
            </div>
            <div className="flex items-center gap-4">
              <div className="flex flex-col">
                <span className="text-[10px] text-muted-foreground font-bold uppercase tracking-widest">Hiển thị</span>
                <span className="text-sm font-bold text-white/90">
                  {filteredNodes.filter(n => !n.data.isDimmed).length} Nút • {edges.length} Cạnh
                </span>
              </div>
              <Button variant="ghost" size="icon" className="rounded-xl h-10 w-10" onClick={fetchGraphData} disabled={isLoading}>
                <RefreshCcw className={cn("w-4 h-4", isLoading && "animate-spin")} />
              </Button>
            </div>
          </Card>
        </div>

        {/* Search Input */}
        {searchOpen && (
          <div className="absolute top-6 right-6 z-10 w-72">
            <Card className="glass px-4 py-3 border-white/10 shadow-2xl flex items-center gap-3">
              <Search className="w-4 h-4 text-muted-foreground shrink-0" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Tìm kiếm entity..."
                aria-label="Search entities"
                className="flex-1 bg-transparent text-sm text-white placeholder:text-muted-foreground focus:outline-none"
                autoFocus
              />
              <button onClick={() => { setSearchOpen(false); setSearchQuery(''); }}>
                <X className="w-4 h-4 text-muted-foreground hover:text-white" />
              </button>
            </Card>
          </div>
        )}

        {/* Toolbox Overlay */}
        <div className="absolute bottom-6 right-6 z-10 flex flex-col gap-3">
          <Card className="glass p-2 border-white/10 shadow-2xl flex flex-col gap-2">
            <Button
              variant="ghost"
              size="icon"
              className="rounded-lg h-9 w-9 text-muted-foreground hover:bg-primary/10 hover:text-primary transition-all"
              onClick={() => { /* Fit view handled by Controls */ }}
              title="Fit View"
            >
              <Maximize2 className="w-4 h-4" />
            </Button>
            <Button
              variant="ghost"
              size="icon"
              className="rounded-lg h-9 w-9 text-muted-foreground hover:bg-primary/10 hover:text-primary transition-all"
              title="Filter (coming soon)"
            >
              <Filter className="w-4 h-4" />
            </Button>
            <Button
              variant="ghost"
              size="icon"
              className={cn(
                "rounded-lg h-9 w-9 transition-all",
                searchOpen ? "bg-primary/10 text-primary" : "text-muted-foreground hover:bg-primary/10 hover:text-primary"
              )}
              onClick={() => setSearchOpen(!searchOpen)}
              title="Search entities"
            >
              <Search className="w-4 h-4" />
            </Button>
          </Card>
          <Card className="glass flex items-center gap-3 px-4 py-2 border-white/10 shadow-2xl">
            <div className="flex items-center gap-2">
              <MousePointer2 className="w-3.5 h-3.5 text-primary" />
              <span className="text-[10px] font-bold text-white uppercase tracking-widest">Click node để xem chi tiết</span>
            </div>
          </Card>
        </div>

        {/* React Flow or Empty State */}
        {hasData ? (
          <ReactFlow
            nodes={filteredNodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onNodeClick={onNodeClick}
            nodeTypes={nodeTypes}
            edgeTypes={edgeTypes}
            fitView
            className="bg-transparent"
            defaultEdgeOptions={{
              type: 'graphEdge',
            }}
          >
            <Background color="#1e293b" gap={20} size={1} />
            <Controls className="bg-white/5 border-white/10 fill-white !shadow-none rounded-xl overflow-hidden" />
            <MiniMap
              className="!bg-black/50 border border-white/5 rounded-2xl !bottom-24 !right-6"
              nodeColor="#6366f1"
              maskColor="rgba(0,0,0,0.4)"
            />
          </ReactFlow>
        ) : !isLoading ? (
          /* S7.6: Empty State */
          <div className="flex flex-col items-center justify-center h-full text-center px-8">
            <div className="w-20 h-20 rounded-3xl bg-white/5 border border-white/10 flex items-center justify-center mb-6">
              <Network className="w-10 h-10 text-muted-foreground/40" />
            </div>
            <h3 className="text-xl font-bold text-white mb-2">Chưa có Knowledge Graph</h3>
            <p className="text-muted-foreground text-sm max-w-md">
              Hãy upload và xử lý tài liệu PDF để hệ thống tự động xây dựng bản đồ tri thức.
            </p>
          </div>
        ) : null}

        {/* Loading Overlay */}
        {isLoading && (
          <div className="absolute inset-0 bg-black/40 backdrop-blur-sm z-50 flex flex-col items-center justify-center gap-4">
            <Loader2 className="w-10 h-10 text-primary animate-spin" />
            <span className="font-bold text-white tracking-widest uppercase text-xs animate-pulse">Đang ánh xạ tri thức...</span>
          </div>
        )}
      </div>

      {/* S7.5: Graph Sidebar */}
      <GraphSidebar
        isOpen={sidebarOpen}
        onClose={() => { setSidebarOpen(false); setSelectedEntity(null); }}
        entity={selectedEntity}
        documentId={documentId!}
      />
    </div>
  );
}
