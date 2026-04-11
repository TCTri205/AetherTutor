/**
 * Utility to export graph data to SVG format.
 * Converts node/edge data into an SVG representation.
 */

interface GraphNode {
  id: string;
  x: number;
  y: number;
  name: string;
  val: number;
  type?: string;
  source?: string;
  tags?: string[];
}

interface GraphLink {
  id: string;
  source: GraphNode;
  target: GraphNode;
  label?: string;
}

interface GraphData {
  nodes: GraphNode[];
  links: GraphLink[];
}

const typeColors: Record<string, string> = {
  concept: '#6366f1',
  term: '#f59e0b',
  process: '#10b981',
  theory: '#a855f7',
  note: '#06b6d4',
};

const relationColors: Record<string, string> = {
  explains: '#10b981',
  contradicts: '#ef4444',
  supports: '#3b82f6',
  defines: '#6366f1',
  mentions: '#94a3b8',
  'related to': '#94a3b8',
};

/**
 * Export graph data to SVG string.
 */
export function exportGraphToSVG(
  graphData: GraphData,
  options: {
    width?: number;
    height?: number;
    backgroundColor?: string;
    showLabels?: boolean;
    showEdgeLabels?: boolean;
  } = {}
): string {
  const {
    width = 1920,
    height = 1080,
    backgroundColor = '#020617',
    showLabels = true,
    showEdgeLabels = true,
  } = options;

  let svg = `<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}" viewBox="0 0 ${width} ${height}">
  <rect width="100%" height="100%" fill="${backgroundColor}"/>
  <g id="graph">
`;

  // Draw edges first (behind nodes)
  graphData.links.forEach((link) => {
    const source = link.source;
    const target = link.target;
    const edgeColor = relationColors[link.label?.toLowerCase() || ''] || '#94a3b8';

    svg += `    <line x1="${source.x}" y1="${source.y}" x2="${target.x}" y2="${target.y}" stroke="${edgeColor}" stroke-width="2" opacity="0.6"/>\n`;

    // Edge label
    if (showEdgeLabels && link.label) {
      const midX = (source.x + target.x) / 2;
      const midY = (source.y + target.y) / 2;
      svg += `    <text x="${midX}" y="${midY}" fill="${edgeColor}" font-size="10" font-style="italic" text-anchor="middle" dominant-baseline="middle">${escapeXml(link.label)}</text>\n`;
    }
  });

  // Draw nodes
  graphData.nodes.forEach((node) => {
    const nodeColor = typeColors[node.type?.toLowerCase() || ''] || '#94a3b8';

    // Node circle
    svg += `    <g id="node-${node.id}">\n`;
    svg += `      <circle cx="${node.x}" cy="${node.y}" r="${node.val}" fill="${nodeColor}" stroke="#ffffff" stroke-width="2"/>\n`;

    // Source badge (Obsidian)
    if (node.source === 'obsidian_import') {
      const badgeX = node.x + node.val * 0.7;
      const badgeY = node.y - node.val * 0.7;
      const badgeSize = node.val * 0.6;
      svg += `      <circle cx="${badgeX}" cy="${badgeY}" r="${badgeSize / 2}" fill="#a855f7" stroke="#fff" stroke-width="1"/>\n`;
      svg += `      <text x="${badgeX}" y="${badgeY}" fill="#fff" font-size="${badgeSize * 0.8}" font-weight="bold" text-anchor="middle" dominant-baseline="middle">O</text>\n`;
    }

    // Label
    if (showLabels) {
      svg += `      <text x="${node.x}" y="${node.y + node.val + 14}" fill="#ffffff" font-size="12" text-anchor="middle" dominant-baseline="middle">${escapeXml(node.name)}</text>\n`;
    }

    svg += `    </g>\n`;
  });

  svg += `  </g>
</svg>`;

  return svg;
}

/**
 * Download SVG as file.
 */
export function downloadSVG(svgContent: string, filename: string): void {
  const blob = new Blob([svgContent], { type: 'image/svg+xml;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

/**
 * Escape XML special characters.
 */
function escapeXml(text: string): string {
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&apos;');
}
