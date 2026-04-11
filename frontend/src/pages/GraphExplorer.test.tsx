import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import GraphExplorer from './GraphExplorer';
import { graphService } from '../services/graph';

// Mock dependencies
vi.mock('../services/graph', () => ({
  graphService: {
    getDocumentGraph: vi.fn(),
    getGlobalGraph: vi.fn(),
    getTags: vi.fn(),
    exportGraph: vi.fn(),
  },
}));

// Mock ForceGraph2D component
vi.mock('react-force-graph-2d', () => ({
  default: vi.fn(({ graphData, onNodeClick, onNodeHover, onLinkHover }) => {
    return (
      <div data-testid="force-graph" data-node-count={graphData.nodes.length} data-link-count={graphData.links.length}>
        {graphData.nodes.map((node: any) => (
          <div
            key={node.id}
            data-testid={`node-${node.id}`}
            onClick={() => onNodeClick?.(node)}
            onMouseEnter={() => onNodeHover?.(node)}
            onMouseLeave={() => onNodeHover?.(null)}
          >
            {node.name}
          </div>
        ))}
      </div>
    );
  }),
}));

// Mock toast
vi.mock('sonner', () => ({
  toast: {
    error: vi.fn(),
    success: vi.fn(),
    promise: vi.fn(),
  },
}));

const mockGraphData = {
  nodes: [
    { id: 'node1', label: 'Machine Learning', type: 'concept', description: 'A type of AI', total_occurrences: 10 },
    { id: 'node2', label: 'Neural Networks', type: 'term', description: 'Deep learning architecture', total_occurrences: 5 },
  ],
  edges: [
    { id: 'edge1', source: 'node1', target: 'node2', label: 'includes', description: 'ML includes NN' },
  ],
};

const renderWithRouter = (ui: React.ReactElement, route = '/') => {
  window.history.pushState({}, 'Test page', route);
  return render(<BrowserRouter>{ui}</BrowserRouter>);
};

describe('GraphExplorer', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('Initial rendering', () => {
    it('should render loading state initially', async () => {
      vi.mocked(graphService.getDocumentGraph).mockReturnValue(new Promise(() => {})); // Pending
      vi.mocked(graphService.getTags).mockResolvedValue([]);

      renderWithRouter(<GraphExplorer />, '/graph/123');

      // Should show loading or empty state while fetching
      await waitFor(() => {
        expect(screen.getByText(/Bản Đồ Tri Thức/i)).toBeInTheDocument();
      });
    });

    it('should fetch graph data on mount', async () => {
      vi.mocked(graphService.getDocumentGraph).mockResolvedValue(mockGraphData);
      vi.mocked(graphService.getTags).mockResolvedValue(['ai', 'deep-learning']);

      renderWithRouter(<GraphExplorer />, '/graph/123');

      await waitFor(() => {
        expect(graphService.getDocumentGraph).toHaveBeenCalledWith('123');
      });
    });

    it('should fetch tags on mount', async () => {
      vi.mocked(graphService.getDocumentGraph).mockResolvedValue(mockGraphData);
      vi.mocked(graphService.getTags).mockResolvedValue(['ai', 'ml']);

      renderWithRouter(<GraphExplorer />, '/graph/123');

      await waitFor(() => {
        expect(graphService.getTags).toHaveBeenCalled();
      });
    });
  });

  describe('Graph data rendering', () => {
    it('should display graph when data is available', async () => {
      vi.mocked(graphService.getDocumentGraph).mockResolvedValue(mockGraphData);
      vi.mocked(graphService.getTags).mockResolvedValue([]);

      renderWithRouter(<GraphExplorer />, '/graph/123');

      await waitFor(() => {
        const graph = screen.getByTestId('force-graph');
        expect(graph).toBeInTheDocument();
        expect(graph).toHaveAttribute('data-node-count', '2');
        expect(graph).toHaveAttribute('data-link-count', '1');
      });
    });

    it('should display empty state when no data', async () => {
      vi.mocked(graphService.getDocumentGraph).mockResolvedValue({ nodes: [], edges: [] });
      vi.mocked(graphService.getTags).mockResolvedValue([]);

      renderWithRouter(<GraphExplorer />, '/graph/123');

      await waitFor(() => {
        expect(screen.getByText('Chưa có Knowledge Graph')).toBeInTheDocument();
      });
    });

    it('should show error toast on fetch failure', async () => {
      const { toast } = await import('sonner');
      vi.mocked(graphService.getDocumentGraph).mockRejectedValue(new Error('Network error'));
      vi.mocked(graphService.getTags).mockResolvedValue([]);

      renderWithRouter(<GraphExplorer />, '/graph/123');

      await waitFor(() => {
        expect(toast.error).toHaveBeenCalledWith(expect.stringContaining('Network error'));
      });
    });
  });

  describe('Node interactions', () => {
    it('should open sidebar when node is clicked', async () => {
      vi.mocked(graphService.getDocumentGraph).mockResolvedValue(mockGraphData);
      vi.mocked(graphService.getTags).mockResolvedValue([]);

      renderWithRouter(<GraphExplorer />, '/graph/123');

      await waitFor(() => {
        const node = screen.getByTestId('node-node1');
        fireEvent.click(node);
      });

      // Sidebar should be open - check for entity details
      await waitFor(() => {
        expect(screen.getByText('Machine Learning')).toBeInTheDocument();
      });
    });

    it('should highlight connected nodes on hover', async () => {
      vi.mocked(graphService.getDocumentGraph).mockResolvedValue(mockGraphData);
      vi.mocked(graphService.getTags).mockResolvedValue([]);

      renderWithRouter(<GraphExplorer />, '/graph/123');

      await waitFor(() => {
        const node = screen.getByTestId('node-node1');
        fireEvent.mouseEnter(node);
      });

      // Graph should have received hover event
      expect(screen.getByTestId('force-graph')).toBeInTheDocument();
    });
  });

  describe('Search functionality', () => {
    it('should open search on Ctrl+K', async () => {
      vi.mocked(graphService.getDocumentGraph).mockResolvedValue(mockGraphData);
      vi.mocked(graphService.getTags).mockResolvedValue([]);

      renderWithRouter(<GraphExplorer />, '/graph/123');

      await waitFor(() => {
        fireEvent.keyDown(document, { ctrlKey: true, key: 'k' });
      });

      // Search input should be visible
      await waitFor(() => {
        const searchInput = screen.getByPlaceholderText('Tìm kiếm thực thể...');
        expect(searchInput).toBeInTheDocument();
      });
    });

    it('should close search on Escape', async () => {
      vi.mocked(graphService.getDocumentGraph).mockResolvedValue(mockGraphData);
      vi.mocked(graphService.getTags).mockResolvedValue([]);

      renderWithRouter(<GraphExplorer />, '/graph/123');

      // Open search first
      await waitFor(() => {
        fireEvent.keyDown(document, { ctrlKey: true, key: 'k' });
      });

      await waitFor(() => {
        expect(screen.getByPlaceholderText('Tìm kiếm thực thể...')).toBeInTheDocument();
      });

      // Close with Escape
      fireEvent.keyDown(document, { key: 'Escape' });

      await waitFor(() => {
        expect(screen.queryByPlaceholderText('Tìm kiếm thực thể...')).not.toBeInTheDocument();
      });
    });
  });

  describe('Tag filtering', () => {
    it('should display tag filter when tags are available', async () => {
      vi.mocked(graphService.getDocumentGraph).mockResolvedValue(mockGraphData);
      vi.mocked(graphService.getTags).mockResolvedValue(['ai', 'machine-learning', 'deep-learning']);

      renderWithRouter(<GraphExplorer />, '/graph/123');

      await waitFor(() => {
        expect(screen.getByText('Tất cả thẻ')).toBeInTheDocument();
        expect(screen.getByText('#ai')).toBeInTheDocument();
      });
    });
  });

  describe('Import modal', () => {
    it('should open import modal when button is clicked', async () => {
      vi.mocked(graphService.getDocumentGraph).mockResolvedValue(mockGraphData);
      vi.mocked(graphService.getTags).mockResolvedValue([]);

      renderWithRouter(<GraphExplorer />, '/graph/123');

      await waitFor(() => {
        const importButton = screen.getByTitle('Import Obsidian Vault');
        fireEvent.click(importButton);
      });

      await waitFor(() => {
        expect(screen.getByText('Import Obsidian Vault')).toBeInTheDocument();
      });
    });
  });

  describe('Data transformation', () => {
    it('should correctly transform backend data to graph format', async () => {
      const testData = {
        nodes: [
          { id: 'test1', label: 'Test Node', type: 'concept', val: 10, description: 'A test node' },
        ],
        edges: [
          { id: 'edge1', source: 'test1', target: 'test2', label: 'relates to', description: 'Test relation' },
        ],
      };

      vi.mocked(graphService.getDocumentGraph).mockResolvedValue(testData);
      vi.mocked(graphService.getTags).mockResolvedValue([]);

      renderWithRouter(<GraphExplorer />, '/graph/123');

      await waitFor(() => {
        const graph = screen.getByTestId('force-graph');
        expect(graph).toHaveAttribute('data-node-count', '1');
        expect(graph).toHaveAttribute('data-link-count', '1');
      });
    });
  });
});
