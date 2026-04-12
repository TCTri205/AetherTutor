import '../styles/tokens.css';
import { useEffect, useState, useCallback, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { graphService } from '../services/graph';
import { exportGraphToSVG, downloadSVG } from '../lib/svgExport';
import {
  Network,
  RefreshCcw,
  Maximize2,
  Zap,
  MousePointer2,
  Loader2,
  Download,
  FolderOpen,
  Users,
  Layers,
  Globe,
  X,
  FileText,
  Share2,
} from 'lucide-react';
import { Button } from '../components/ui/Button';
import { Card } from '../components/ui/Card';
import GraphSidebar from '../components/graph/GraphSidebar';
import GraphView, { type GraphViewRef } from '../components/graph/GraphView';
import AliasManager from '../components/graph/AliasManager';
import MultiDocQuery from '../components/graph/MultiDocQuery';
import TagFilter from '../components/graph/TagFilter';
import { cn } from '../lib/utils';
import { toast } from 'sonner';

// ─── Main Component ────────────────────────────────────────────
export default function GlobalGraphExplorer() {
  const navigate = useNavigate();
  const graphViewRef = useRef<GraphViewRef>(null);

  const [graphData, setGraphData] = useState<{ nodes: any[]; links: any[] }>({ nodes: [], links: [] });
  const [isLoading, setIsLoading] = useState(false);
  const [hasData, setHasData] = useState(false);

  const [selectedEntity, setSelectedEntity] = useState<any>(null);
  const [sidebarOpen, setSidebarOpen] = useState(false);

  // Tag filtering
  const [allTags, setAllTags] = useState<string[]>([]);
  const [selectedTag, setSelectedTag] = useState<string | null>(null);
  const [tagEntityCounts, setTagEntityCounts] = useState<Record<string, number>>({});

  // Document filter (optional - for multi-doc view)
  const [availableDocs, setAvailableDocs] = useState<Array<{id: string, name: string}>>([]);
  const [selectedDocs, setSelectedDocs] = useState<string[]>([]);

  // Modals
  const [activePanel, setActivePanel] = useState<'aliases' | 'multi-query' | null>(null);

  // Fetch global graph data
  const fetchGraphData = useCallback(async () => {
    setIsLoading(true);
    try {
      const data = await graphService.getGlobalGraph();

      if (!data.nodes || data.nodes.length === 0) {
        setHasData(false);
        setGraphData({ nodes: [], links: [] });
        setIsLoading(false);
        return;
      }

      setHasData(true);

      const formattedData = {
        nodes: data.nodes.map((node: any) => ({
          ...node,
          id: node.id,
          name: node.label || node.id,
          val: node.val || (node.total_occurrences ? Math.sqrt(node.total_occurrences) * 5 : 5),
        })),
        links: data.edges.map((edge: any) => ({
          ...edge,
          id: edge.id || `${edge.source}-${edge.target}`,
          source: edge.source,
          target: edge.target,
          label: edge.label || '',
        })),
      };

      setGraphData(formattedData);

    } catch (err: any) {
      toast.error(`Lỗi tải đồ thị toàn cục: ${err.message}`);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchGraphData();

    // Fetch tags
    const fetchTags = async () => {
      try {
        const tags = await graphService.getTags();
        setAllTags(tags);

        // Count entities per tag
        const counts: Record<string, number> = {};
        tags.forEach(tag => {
          counts[tag] = graphData.nodes.filter((n: any) => 
            n.tags && n.tags.includes(tag)
          ).length;
        });
        setTagEntityCounts(counts);
      } catch (err) {
        console.error("Failed to fetch tags", err);
      }
    };
    fetchTags();

    // Keyboard Shortcuts
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        setSidebarOpen(false);
        setActivePanel(null);
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [fetchGraphData, graphData]);

  // Node Click → sidebar
  const handleNodeClick = useCallback((node: any) => {
    const neighbors = graphData.links
      .filter(l => l.source.id === node.id || l.target.id === node.id)
      .map(l => ({
        target: l.source.id === node.id ? l.target.id : l.source.id,
        relation_type: l.label,
        description: l.description,
      }));

    setSelectedEntity({
      id: node.id,
      label: node.name,
      type: node.type,
      description: node.description,
      neighbors,
      degree: neighbors.length,
      documents: node.documents || [], // Multi-doc info
    });
    setSidebarOpen(true);
  }, [graphData]);

  // Navigate to document-specific graph
  const navigateToDocGraph = (docId: string) => {
    navigate(`/graph/${docId}`);
  };

  // Export functions
  const exportToSVG = useCallback(() => {
    if (graphData.nodes.length === 0) {
      toast.error('Không có dữ liệu để xuất SVG');
      return;
    }

    try {
      const svgContent = exportGraphToSVG(graphData, {
        width: 1920,
        height: 1080,
        backgroundColor: '#020617',
        showLabels: true,
        showEdgeLabels: true,
      });
      downloadSVG(svgContent, 'graph-global.svg');
      toast.success('Đã tải xuống file SVG!');
    } catch (err) {
      toast.error('Lỗi khi xuất SVG');
    }
  }, [graphData]);

  return (
    <div className="flex h-full overflow-hidden bg-primary rounded-3xl border border-border-primary relative">
      <div className="flex-1 relative">
        {/* Header Overlay */}
        <div className="absolute top-6 left-6 z-10 flex items-center gap-4 pointer-events-none">
          <Card className="glass px-6 py-4 border-border-primary shadow-2xl flex items-center gap-6 pointer-events-auto">
            <div className="flex items-center gap-3 pr-6 border-r border-border-primary font-bold text-primary tracking-tight">
              <Globe className="w-5 h-5 text-primary" />
              Bản Đồ Tri Thức Toàn Cục
            </div>
            <div className="flex items-center gap-4">
              <div className="flex flex-col">
                <span className="text-[10px] text-secondary font-bold uppercase tracking-widest">Hiển thị</span>
                <span className="text-sm font-bold text-primary">
                  {graphData.nodes.length} Nút • {graphData.links.length} Cạnh
                </span>
              </div>

              {/* Tag Selection */}
              {allTags.length > 0 && (
                <div className="flex items-center gap-2 pl-4 border-l border-border-primary shrink-0">
                  <select
                    className="bg-transparent text-xs text-primary border-none focus:outline-none cursor-pointer"
                    value={selectedTag || ''}
                    onChange={(e) => setSelectedTag(e.target.value || null)}
                  >
                    <option value="" className="bg-primary">Tất cả thẻ</option>
                    {allTags.map(tag => (
                      <option key={tag} value={tag} className="bg-primary">#{tag}</option>
                    ))}
                  </select>
                </div>
              )}

              <Button variant="ghost" size="icon" className="rounded-xl h-10 w-10 shrink-0" onClick={fetchGraphData} disabled={isLoading}>
                <RefreshCcw className={cn("w-4 h-4", isLoading && "animate-spin")} />
              </Button>
            </div>
          </Card>
        </div>

        {/* Toolbox Overlay */}
        <div className="absolute bottom-6 right-6 z-10 flex flex-col gap-3">
          <Card className="glass p-2 border-white/10 shadow-2xl flex flex-col gap-2">
            <Button
              variant="ghost"
              size="icon"
              className="rounded-lg h-9 w-9 text-muted-foreground hover:bg-primary/10 hover:text-primary transition-all"
              onClick={() => graphViewRef.current?.zoomToFit(400, 100)}
              title="Fit View"
            >
              <Maximize2 className="w-4 h-4" />
            </Button>
            <Button
              variant="ghost"
              size="icon"
              className="rounded-lg h-9 w-9 text-muted-foreground hover:bg-primary/10 hover:text-primary transition-all"
              onClick={exportToSVG}
              title="Export Graph (PNG)"
            >
              <Download className="w-4 h-4" />
            </Button>
            <Button
              variant="ghost"
              size="icon"
              className="rounded-lg h-9 w-9 text-muted-foreground hover:bg-primary/10 hover:text-primary transition-all"
              onClick={exportToSVG}
              title="Export as SVG"
            >
              <Download className="w-4 h-4" />
            </Button>
            <Button
              variant="ghost"
              size="icon"
              className="rounded-lg h-9 w-9 text-muted-foreground hover:bg-primary/10 hover:text-primary transition-all"
              onClick={() => setActivePanel('aliases')}
              title="Manage Aliases"
            >
              <Users className="w-4 h-4" />
            </Button>
            <Button
              variant="ghost"
              size="icon"
              className="rounded-lg h-9 w-9 text-muted-foreground hover:bg-primary/10 hover:text-primary transition-all"
              onClick={() => setActivePanel('multi-query')}
              title="Cross-Document Query"
            >
              <Layers className="w-4 h-4" />
            </Button>
            <Button
              variant="ghost"
              size="icon"
              className="rounded-lg h-9 w-9 text-muted-foreground hover:bg-primary/10 hover:text-primary transition-all"
              onClick={() => navigate('/graph')}
              title="Back to Document Graph"
            >
              <FileText className="w-4 h-4" />
            </Button>
          </Card>
        </div>

        {/* Help text */}
        <div className="absolute bottom-6 left-6 z-10 pointer-events-none">
          <Card className="glass flex items-center gap-3 px-4 py-2 border-border-primary shadow-2xl">
            <div className="flex items-center gap-2">
              <MousePointer2 className="w-3.5 h-3.5 text-primary" />
              <span className="text-[10px] font-bold text-primary uppercase tracking-widest">
                Kéo để di chuyển • Cuộn để phóng to • Click nút để xem chi tiết
              </span>
            </div>
          </Card>
        </div>

        {/* Graph Component */}
        {hasData ? (
          <GraphView
            ref={graphViewRef}
            data={graphData}
            onNodeClick={handleNodeClick}
            isLoading={isLoading}
            selectedTag={selectedTag}
            showObsidianBadges={false}
          />
        ) : !isLoading ? (
          <div className="flex flex-col items-center justify-center h-full text-center px-8">
            <div className="w-20 h-20 rounded-3xl bg-secondary border border-border-primary flex items-center justify-center mb-6">
              <Globe className="w-10 h-10 text-tertiary" />
            </div>
            <h3 className="text-xl font-bold text-primary mb-2">Chưa có đồ thị toàn cục</h3>
            <p className="text-secondary text-sm max-w-md">
              Hãy xử lý nhiều tài liệu để xây dựng đồ thị tri thức liên văn bản.
            </p>
          </div>
        ) : null}

        {/* Loading Overlay */}
        {isLoading && (
          <div className="absolute inset-0 bg-overlay backdrop-blur-sm z-50 flex flex-col items-center justify-center gap-4">
            <Loader2 className="w-10 h-10 text-primary animate-spin" />
            <span className="font-bold text-primary tracking-widest uppercase text-xs animate-pulse">Đang ánh xạ tri thức toàn cục...</span>
          </div>
        )}
      </div>

      {/* Sidebar */}
      <GraphSidebar
        isOpen={sidebarOpen}
        onClose={() => { setSidebarOpen(false); setSelectedEntity(null); }}
        entity={selectedEntity}
        documentId={selectedEntity?.documents?.[0]} // Use first document if available
      />

      {/* Advanced Panels (Alias Manager & Multi Query) */}
      {activePanel && (
        <div className="absolute inset-0 z-[110] flex items-center justify-center bg-overlay backdrop-blur-md p-6">
          <Card className="glass w-full max-w-4xl max-h-[90vh] flex flex-col border-border-primary shadow-2xl relative overflow-hidden">
             <div className="flex items-center justify-between p-6 border-b border-border-primary">
                <h3 className="text-xl font-bold text-primary flex items-center gap-3">
                  {activePanel === 'aliases' && <><Users className="w-6 h-6 text-primary" />Quản lý Bí danh</>}
                  {activePanel === 'multi-query' && <><Layers className="w-6 h-6 text-primary" />Truy vấn Đa tài liệu</>}
                </h3>
                <button
                  onClick={() => setActivePanel(null)}
                  className="text-secondary hover:text-primary"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>
              
              <div className="flex-1 overflow-y-auto p-6">
                {activePanel === 'aliases' && <AliasManager />}
                {activePanel === 'multi-query' && <MultiDocQuery />}
              </div>
          </Card>
        </div>
      )}
    </div>
  );
}
