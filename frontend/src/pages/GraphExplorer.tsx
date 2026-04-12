import { useEffect, useState, useCallback, useRef } from 'react';
import { useParams, useLocation } from 'react-router-dom';
import { graphService } from '../services/graph';
import { exportGraphToSVG, downloadSVG } from '../lib/svgExport';
import {
  Network,
  RefreshCcw,
  Maximize2,
  Tag,
  Search,
  Zap,
  MousePointer2,
  Loader2,
  Share2,
  MessageSquare,
  X,
  Download,
  FolderOpen,
  Users,
  Layers,
  GitGraph,
} from 'lucide-react';
import { Button } from '../components/ui/Button';
import { Card } from '../components/ui/Card';
import GraphSidebar from '../components/graph/GraphSidebar';
import GraphView, { type GraphViewRef } from '../components/graph/GraphView';
import GraphSearchBar from '../components/graph/GraphSearchBar';
import AliasManager from '../components/graph/AliasManager';
import MultiDocQuery from '../components/graph/MultiDocQuery';
import MermaidDiagram from '../components/shared/MermaidDiagram';
import { cn } from '../lib/utils';
import { toast } from 'sonner';

// ─── Main Component ────────────────────────────────────────────
export default function GraphExplorer() {
  const { documentId } = useParams<{ documentId: string }>();
  const location = useLocation();
  const graphViewRef = useRef<GraphViewRef>(null);

  const [graphData, setGraphData] = useState<{ nodes: any[]; links: any[] }>({ nodes: [], links: [] });
  const [isLoading, setIsLoading] = useState(false);
  const [hasData, setHasData] = useState(false);

  // Diagram view state
  const [activeTab, setActiveTab] = useState<'graph' | 'diagram'>('graph');
  const [mermaidCode, setMermaidCode] = useState<string>('');
  const [mermaidMetadata, setMermaidMetadata] = useState<any>(null);
  const [isGeneratingDiagram, setIsGeneratingDiagram] = useState(false);

  const [searchQuery, setSearchQuery] = useState('');
  const [searchOpen, setSearchOpen] = useState(false);
  const [selectedEntity, setSelectedEntity] = useState<any>(null);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  
  // Import Obsidian State
  const [isImportModalOpen, setIsImportModalOpen] = useState(false);
  const [vaultPath, setVaultPath] = useState('');
  const [importStatus, setImportStatus] = useState<any>(null);
  const [isImporting, setIsImporting] = useState(false);

  // New features
  const [allTags, setAllTags] = useState<string[]>([]);
  const [selectedTag, setSelectedTag] = useState<string | null>(null);
  const [isGlobalMode, setIsGlobalMode] = useState(false);
  
  // Modals
  const [activePanel, setActivePanel] = useState<'aliases' | 'multi-query' | null>(null);

  // Fetch graph data
  const fetchGraphData = useCallback(async () => {
    setIsLoading(true);
    try {
      let data: any;
      if (documentId) {
        data = await graphService.getDocumentGraph(documentId);
      } else {
        data = await graphService.getGlobalGraph();
        setIsGlobalMode(true);
      }

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
      toast.error(`Lỗi tải đồ thị: ${err.message}`);
    } finally {
      setIsLoading(false);
    }
  }, [documentId]);

  useEffect(() => {
    fetchGraphData();
    
    // Fetch tags
    const fetchTags = async () => {
      try {
        const tags = await graphService.getTags();
        setAllTags(tags);
      } catch (err) {
        console.error("Failed to fetch tags", err);
      }
    };
    fetchTags();

    // Keyboard Shortcuts
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault();
        setSearchOpen(prev => !prev);
      }
      if (e.key === 'Escape') {
        setSearchOpen(false);
        setSidebarOpen(false);
        setActivePanel(null);
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [fetchGraphData]);

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
    });
    setSidebarOpen(true);
  }, [graphData]);

  // Handle Obsidian Import
  const startImport = async () => {
    if (!vaultPath.trim()) return;
    setIsImporting(true);
    try {
      const response = await fetch('/api/v1/graph/import/obsidian', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ vault_path: vaultPath }),
      });
      const data = await response.json();
      if (data.job_id) {
        pollImportStatus(data.job_id);
      }
    } catch (err: any) {
      toast.error(`Lỗi khởi tạo import: ${err.message}`);
      setIsImporting(false);
    }
  };

  const pollImportStatus = async (jobId: string) => {
    const interval = setInterval(async () => {
      try {
        const response = await fetch(`/api/v1/graph/import/obsidian/status/${jobId}`);
        const data = await response.json();
        setImportStatus(data);
        
        if (data.status === 'completed' || data.status === 'failed') {
          clearInterval(interval);
          setIsImporting(false);
          if (data.status === 'completed') {
            toast.success("Import Obsidian hoàn tất!");
            fetchGraphData();
            setIsImportModalOpen(false);
          } else {
            toast.error(`Import thất bại: ${data.error}`);
          }
        }
      } catch (err) {
        clearInterval(interval);
        setIsImporting(false);
      }
    }, 2000);
  };

  const exportToGraphML = useCallback(async () => {
    if (!documentId) return;
    try {
      const blob = await graphService.exportGraph(documentId, 'graphml');
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `graph_${documentId}.graphml`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      toast.success('Đã tải xuống file GraphML!');
    } catch (err) {
      toast.error('Lỗi khi xuất GraphML');
    }
  }, [documentId]);

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
      downloadSVG(svgContent, `graph-${documentId || 'export'}.svg`);
      toast.success('Đã tải xuống file SVG!');
    } catch (err) {
      toast.error('Lỗi khi xuất SVG');
    }
  }, [graphData, documentId]);

  // Generate Mermaid diagram
  const generateMermaidDiagram = useCallback(async (format: string = 'mindmap') => {
    if (graphData.nodes.length === 0) {
      toast.error('Không có dữ liệu để tạo diagram');
      return;
    }

    setIsGeneratingDiagram(true);
    try {
      // Convert graphData to format for API
      const nodes = graphData.nodes.map((n: any) => ({
        id: n.id,
        name: n.label || n.name || n.id,
        type: n.type || n.entity_type || 'concept',
        description: n.description || '',
        confidence: n.confidence || 0.5,
      }));

      const edges = graphData.links.map((l: any) => ({
        source: typeof l.source === 'object' ? l.source.id : l.source,
        target: typeof l.target === 'object' ? l.target.id : l.target,
        label: l.label || l.relation_type || '',
        description: l.description || '',
      }));

      // Call API
      const response = await fetch('/api/v1/graph/mermaid', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          document_id: documentId,
          max_nodes: 100,
          max_depth: 3,
          format,
        }),
      });

      if (!response.ok) {
        throw new Error('API call failed');
      }

      const data = await response.json();
      setMermaidCode(data.mermaid_code);
      setMermaidMetadata(data.metadata);
      setActiveTab('diagram');
      toast.success('Diagram tạo thành công!');
    } catch (err: any) {
      toast.error(`Lỗi tạo diagram: ${err.message}`);
    } finally {
      setIsGeneratingDiagram(false);
    }
  }, [graphData, documentId]);

  return (
    <div className="flex h-full overflow-hidden bg-[#020617] rounded-3xl border border-white/5 relative">
      <div className="flex-1 relative">
        {/* Header Overlay */}
        <div className="absolute top-6 left-6 z-10 flex items-center gap-4 pointer-events-none">
          <Card className="glass px-6 py-4 border-white/10 shadow-2xl flex items-center gap-6 pointer-events-auto">
            <div className="flex items-center gap-3 pr-6 border-r border-white/10 font-bold text-white tracking-tight">
              <Network className="w-5 h-5 text-primary" />
              Bản Đồ Tri Thức
            </div>
            <div className="flex items-center gap-4">
              <div className="flex flex-col">
                <span className="text-[10px] text-muted-foreground font-bold uppercase tracking-widest">Hiển thị</span>
                <span className="text-sm font-bold text-white/90">
                  {graphData.nodes.length} Nút • {graphData.links.length} Cạnh
                </span>
              </div>
              
              {/* Tag Selection */}
              {allTags.length > 0 && (
                <div className="flex items-center gap-2 pl-4 border-l border-white/10 shrink-0">
                  <Tag className="w-3.5 h-3.5 text-muted-foreground" />
                  <select 
                    className="bg-transparent text-xs text-white border-none focus:outline-none cursor-pointer"
                    value={selectedTag || ''}
                    onChange={(e) => setSelectedTag(e.target.value || null)}
                  >
                    <option value="" className="bg-[#020617]">Tất cả thẻ</option>
                    {allTags.map(tag => (
                      <option key={tag} value={tag} className="bg-[#020617]">#{tag}</option>
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

        {/* Search Bar */}
        {searchOpen && (
          <GraphSearchBar
            nodes={graphData.nodes}
            onNodeSelect={(node) => handleNodeClick(node)}
            onClose={() => { setSearchOpen(false); setSearchQuery(''); }}
          />
        )}

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
              className={cn(
                "rounded-lg h-9 w-9 transition-all",
                searchOpen ? "bg-primary/10 text-primary" : "text-muted-foreground hover:bg-primary/10 hover:text-primary"
              )}
              onClick={() => setSearchOpen(!searchOpen)}
              title="Search entities"
            >
              <Search className="w-4 h-4" />
            </Button>
            <Button
              variant="ghost"
              size="icon"
              className="rounded-lg h-9 w-9 text-muted-foreground hover:bg-primary/10 hover:text-primary transition-all"
              onClick={exportToGraphML}
              title="Export as GraphML"
            >
              <Share2 className="w-4 h-4" />
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
              onClick={() => setIsImportModalOpen(true)}
              title="Import Obsidian Vault"
            >
              <FolderOpen className="w-4 h-4" />
            </Button>
          </Card>
        </div>

        {/* Help text */}
        <div className="absolute bottom-6 left-6 z-10 pointer-events-none">
          <Card className="glass flex items-center gap-3 px-4 py-2 border-white/10 shadow-2xl">
            <div className="flex items-center gap-2">
              <MousePointer2 className="w-3.5 h-3.5 text-primary" />
              <span className="text-[10px] font-bold text-white uppercase tracking-widest">
                Kéo để di chuyển • Cuộn để phóng to • Click nút để xem chi tiết
              </span>
            </div>
          </Card>
        </div>

        {/* Graph Component */}
        {hasData ? (
          <div className="relative h-full">
            {/* Tab Switcher */}
            <div className="absolute top-4 right-6 z-10 flex gap-2">
              <Button
                variant={activeTab === 'graph' ? 'default' : 'outline'}
                size="sm"
                onClick={() => setActiveTab('graph')}
                className={cn(
                  "gap-2 transition-all",
                  activeTab === 'graph'
                    ? "bg-primary text-primary-foreground shadow-lg shadow-primary/30"
                    : "bg-white/5 border-white/10 text-white/70 hover:bg-white/10"
                )}
              >
                <Network className="w-4 h-4" />
                Graph View
              </Button>
              <Button
                variant={activeTab === 'diagram' ? 'default' : 'outline'}
                size="sm"
                onClick={() => setActiveTab('diagram')}
                className={cn(
                  "gap-2 transition-all",
                  activeTab === 'diagram'
                    ? "bg-primary text-primary-foreground shadow-lg shadow-primary/30"
                    : "bg-white/5 border-white/10 text-white/70 hover:bg-white/10"
                )}
              >
                <GitGraph className="w-4 h-4" />
                Diagram
              </Button>
              {activeTab === 'diagram' && !mermaidCode && (
                <div className="flex gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => generateMermaidDiagram('mindmap')}
                    disabled={isGeneratingDiagram}
                    className="bg-white/5 border-white/10 text-white/70 hover:bg-white/10"
                  >
                    {isGeneratingDiagram ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Mindmap'}
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => generateMermaidDiagram('flowchart_td')}
                    disabled={isGeneratingDiagram}
                    className="bg-white/5 border-white/10 text-white/70 hover:bg-white/10"
                  >
                    Flowchart TD
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => generateMermaidDiagram('flowchart_lr')}
                    disabled={isGeneratingDiagram}
                    className="bg-white/5 border-white/10 text-white/70 hover:bg-white/10"
                  >
                    Flowchart LR
                  </Button>
                </div>
              )}
            </div>

            {/* Graph View */}
            {activeTab === 'graph' && (
              <GraphView
                ref={graphViewRef}
                data={graphData}
                onNodeClick={handleNodeClick}
                isLoading={isLoading}
                searchQuery={searchQuery}
                selectedTag={selectedTag}
                showObsidianBadges={true}
              />
            )}

            {/* Diagram View */}
            {activeTab === 'diagram' && (
              <div className="h-full overflow-auto p-6 bg-[#020617]">
                {mermaidCode ? (
                  <MermaidDiagram
                    code={mermaidCode}
                    metadata={mermaidMetadata}
                    className="max-w-4xl mx-auto"
                  />
                ) : (
                  <div className="flex flex-col items-center justify-center h-full text-center px-8">
                    <div className="w-20 h-20 rounded-3xl bg-white/5 border border-white/10 flex items-center justify-center mb-6">
                      <GitGraph className="w-10 h-10 text-muted-foreground/40" />
                    </div>
                    <h3 className="text-xl font-bold text-white mb-2">Chưa có Diagram</h3>
                    <p className="text-muted-foreground text-sm max-w-md mb-6">
                      Chọn định dạng sơ đồ bên trên để tạo Mermaid diagram từ Knowledge Graph.
                    </p>
                  </div>
                )}
              </div>
            )}
          </div>
        ) : !isLoading ? (
          <div className="flex flex-col items-center justify-center h-full text-center px-8">
            <div className="w-20 h-20 rounded-3xl bg-white/5 border border-white/10 flex items-center justify-center mb-6">
              <Network className="w-10 h-10 text-muted-foreground/40" />
            </div>
            <h3 className="text-xl font-bold text-white mb-2">Chưa có Knowledge Graph</h3>
            <p className="text-muted-foreground text-sm max-w-md">
              Hãy tải lên và xử lý tài liệu PDF để hệ thống tự động khởi tạo đồ thị.
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

      {/* Sidebar */}
      <GraphSidebar
        isOpen={sidebarOpen}
        onClose={() => { setSidebarOpen(false); setSelectedEntity(null); }}
        entity={selectedEntity}
        documentId={documentId!}
      />

      {/* Import Modal */}
      {isImportModalOpen && (
        <div className="absolute inset-0 z-[100] flex items-center justify-center bg-black/60 backdrop-blur-md">
          <Card className="glass w-[450px] p-8 border-white/10 shadow-2xl space-y-6">
            <div className="flex items-center justify-between">
              <h3 className="text-xl font-bold text-white flex items-center gap-3">
                <FolderOpen className="w-6 h-6 text-primary" />
                Import Obsidian Vault
              </h3>
              <button 
                onClick={() => setIsImportModalOpen(false)}
                className="text-muted-foreground hover:text-white"
                disabled={isImporting}
              >
                <X className="w-5 h-5" />
              </button>
            </div>
            
            <p className="text-sm text-muted-foreground leading-relaxed">
              Nhập đường dẫn tuyệt đối tới Obsidian Vault của bạn. Hệ thống sẽ trích xuất 
              các ghi chú (`.md`), liên kết wiki và gắn thẻ vào bản đồ tri thức này.
            </p>

            <div className="space-y-4">
              <div className="space-y-2">
                <label className="text-xs font-bold text-muted-foreground uppercase tracking-widest px-1">Đường dẫn Vault</label>
                <input 
                  type="text" 
                  value={vaultPath}
                  onChange={(e) => setVaultPath(e.target.value)}
                  placeholder="e.g. D:\MyNotes\Knowledge"
                  className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-white placeholder:text-muted-foreground focus:ring-2 focus:ring-primary/50 transition-all outline-none"
                  disabled={isImporting}
                />
              </div>
            </div>

            {importStatus && (
              <div className={cn(
                "p-4 rounded-xl border text-sm",
                importStatus.status === 'processing' ? "bg-primary/5 border-primary/20 text-primary animate-pulse" :
                importStatus.status === 'completed' ? "bg-emerald-500/5 border-emerald-500/20 text-emerald-400" :
                importStatus.status === 'failed' ? "bg-rose-500/5 border-rose-500/20 text-rose-400" : ""
              )}>
                {importStatus.status === 'processing' && "Đang xử lý vault..."}
                {importStatus.status === 'completed' && (
                  <div>
                    Import hoàn tất! 
                    <div className="text-[10px] mt-1 opacity-70">
                      Đã nhập: {importStatus.result.entities_imported} thực thể, {importStatus.result.relations_imported} quan hệ.
                    </div>
                  </div>
                )}
                {importStatus.status === 'failed' && `Lỗi: ${importStatus.error}`}
              </div>
            )}

            <Button 
              className="w-full h-12 rounded-xl text-md font-bold"
              onClick={startImport}
              disabled={isImporting || !vaultPath.trim()}
            >
              {isImporting ? (
                <>
                  <Loader2 className="w-5 h-5 animate-spin mr-2" />
                  Đang xử lý...
                </>
              ) : "Bắt đầu Import"}
            </Button>
          </Card>
        </div>
      )}
      {/* Advanced Panels (Alias Manager & Multi Query) */}
      {activePanel && (
        <div className="absolute inset-0 z-[110] flex items-center justify-center bg-black/60 backdrop-blur-md p-6">
          <Card className="glass w-full max-w-4xl max-h-[90vh] flex flex-col border-white/10 shadow-2xl relative overflow-hidden">
             <div className="flex items-center justify-between p-6 border-b border-white/5">
                <h3 className="text-xl font-bold text-white flex items-center gap-3">
                  {activePanel === 'aliases' ? (
                    <><Users className="w-6 h-6 text-primary" /> Quản lý Bí danh thực thể</>
                  ) : (
                    <><Layers className="w-6 h-6 text-primary" /> Truy vấn Xuyên tài liệu</>
                  )}
                </h3>
                <button 
                  onClick={() => setActivePanel(null)}
                  className="p-2 rounded-lg hover:bg-white/10 text-muted-foreground hover:text-white"
                >
                  <X className="w-6 h-6" />
                </button>
             </div>
             <div className="flex-1 overflow-y-auto p-6 bg-[#020617]/50">
                {activePanel === 'aliases' ? <AliasManager /> : <MultiDocQuery />}
             </div>
          </Card>
        </div>
      )}
    </div>
  );
}
