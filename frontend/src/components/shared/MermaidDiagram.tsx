import React, { useEffect, useRef, useState } from 'react';
import mermaid from 'mermaid';
import { ZoomIn, AlertCircle } from 'lucide-react';

interface MermaidDiagramProps {
  code: string;
  metadata?: {
    total_nodes: number;
    total_edges: number;
    truncated: boolean;
    format: string;
  };
  className?: string;
}

// Initialize mermaid once
let mermaidInitialized = false;
const initializeMermaid = () => {
  if (!mermaidInitialized) {
    mermaid.initialize({
      startOnLoad: false,
      theme: 'default',
      securityLevel: 'loose',
      fontFamily: 'system-ui, -apple-system, sans-serif',
      flowchart: {
        useMaxWidth: true,
        htmlLabels: true,
        curve: 'basis',
      },
      mindmap: {
        useMaxWidth: true,
      },
    });
    mermaidInitialized = true;
  }
};

const MermaidDiagram: React.FC<MermaidDiagramProps> = ({
  code,
  metadata,
  className = '',
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const [svgContent, setSvgContent] = useState<string>('');
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [isFullscreen, setIsFullscreen] = useState(false);

  useEffect(() => {
    initializeMermaid();
    renderDiagram();
  }, [code]);

  const renderDiagram = async () => {
    if (!code.trim()) {
      setError('No diagram code provided');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      // Validate mermaid syntax
      const valid = await mermaid.parse(code);
      if (!valid) {
        throw new Error('Invalid Mermaid syntax');
      }

      // Generate unique ID for this diagram
      const id = `mermaid-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;

      // Render the diagram
      const { svg } = await mermaid.render(id, code);
      setSvgContent(svg);
    } catch (err) {
      console.error('Mermaid render error:', err);
      setError(
        err instanceof Error
          ? `Lỗi render diagram: ${err.message}`
          : 'Không thể render diagram. Vui lòng kiểm tra cú pháp.'
      );
    } finally {
      setLoading(false);
    }
  };

  const handleFullscreen = () => {
    setIsFullscreen(!isFullscreen);
  };

  const handleEscape = (e: React.KeyboardEvent) => {
    if (e.key === 'Escape' && isFullscreen) {
      setIsFullscreen(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center p-8 bg-gray-50 dark:bg-gray-900 rounded-lg">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
        <span className="ml-3 text-sm text-gray-600 dark:text-gray-400">
          Đang tạo diagram...
        </span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
        <div className="flex items-start gap-2">
          <AlertCircle className="w-5 h-5 text-red-600 dark:text-red-400 mt-0.5 flex-shrink-0" />
          <div>
            <p className="text-sm font-medium text-red-800 dark:text-red-300">{error}</p>
            <p className="text-xs text-red-600 dark:text-red-400 mt-1">
              Thử định dạng khác hoặc giảm số lượng nodes.
            </p>
          </div>
        </div>
      </div>
    );
  }

  // Metadata badge
  const MetadataBadge = () => {
    if (!metadata) return null;

    return (
      <div className="flex items-center gap-2 mb-2 text-xs text-gray-600 dark:text-gray-400">
        <span className="px-2 py-1 bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 rounded">
          {metadata.total_nodes} nodes
        </span>
        <span className="px-2 py-1 bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300 rounded">
          {metadata.total_edges} edges
        </span>
        {metadata.truncated && (
          <span className="px-2 py-1 bg-yellow-100 dark:bg-yellow-900/30 text-yellow-700 dark:text-yellow-300 rounded">
            ⚠️ Truncated
          </span>
        )}
        <span className="px-2 py-1 bg-gray-100 dark:bg-gray-800 rounded">
          {metadata.format.replace('_', ' ')}
        </span>
      </div>
    );
  };

  return (
    <>
      <div className={`relative group ${className}`} onKeyDown={handleEscape}>
        <MetadataBadge />

        {/* Toolbar */}
        <div className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity z-10">
          <button
            onClick={handleFullscreen}
            className="p-2 bg-white dark:bg-gray-800 rounded-lg shadow-md hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
            title="Zoom to fullscreen"
          >
            <ZoomIn className="w-4 h-4 text-gray-600 dark:text-gray-400" />
          </button>
        </div>

        {/* Diagram */}
        <div
          ref={containerRef}
          className="overflow-auto bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-700 p-4"
          dangerouslySetInnerHTML={{ __html: svgContent }}
        />
      </div>

      {/* Fullscreen modal */}
      {isFullscreen && (
        <div
          className="fixed inset-0 z-50 bg-black/70 flex items-center justify-center p-4"
          onClick={() => setIsFullscreen(false)}
        >
          <div
            className="relative bg-white dark:bg-gray-900 rounded-lg shadow-xl max-w-full max-h-full overflow-auto p-8"
            onClick={(e) => e.stopPropagation()}
          >
            <button
              onClick={handleFullscreen}
              className="absolute top-4 right-4 p-2 bg-gray-100 dark:bg-gray-800 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-700 transition-colors"
              title="Close (Esc)"
            >
              <span className="text-lg">✕</span>
            </button>

            <MetadataBadge />

            <div
              className="mt-4"
              dangerouslySetInnerHTML={{ __html: svgContent }}
            />
          </div>
        </div>
      )}
    </>
  );
};

export default MermaidDiagram;
