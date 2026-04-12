"""
VisualizerAgent - Knowledge Graph to Mermaid Diagram Conversion

Chuyển đổi Knowledge Graph thành các định dạng Mermaid.js diagrams:
- mindmap: Sơ đồ tư duy cho phân tích chủ đề
- graph TD: Flowchart top-down cho quy trình/hệ thống
- graph LR: Flowchart left-right cho mối quan hệ

Features:
- BFS subgraph extraction từ topic root
- Max nodes/depth truncation để tránh diagram quá lớn
- Multiple format support (mindmap, flowchart TD/LR)
- Metadata trả về kèm (total_nodes, total_edges, truncated flag)
"""

from collections import deque
from typing import Dict, List, Any, Optional, Tuple
from loguru import logger


class VisualizerAgent:
    """
    Agent chuyển đổi Knowledge Graph thành Mermaid diagram code.

    Usage:
        agent = VisualizerAgent()
        result = await agent.generate_mermaid(
            graph_data=graph_data,
            topic="Machine Learning",
            max_nodes=100,
            max_depth=3,
            format="mindmap"
        )
        # result = {mermaid_code: "...", metadata: {...}}
    """

    # Mapping entity types sang Mermaid colors
    TYPE_COLORS = {
        "concept": "#4A90D9",
        "person": "#F5A623",
        "place": "#7ED321",
        "event": "#D0021B",
        "process": "#9013FE",
        "object": "#417505",
        "idea": "#BD10E0",
        "default": "#8B8B8B",
    }

    # Relation type icons cho flowchart
    RELATION_ICONS = {
        "is_a": "--> |là|",
        "part_of": "--> |bao gồm|",
        "related_to": "--> |liên quan|",
        "causes": "--> |gây ra|",
        "enables": "--> |cho phép|",
        "prevents": "--> |ngăn chặn|",
        "depends_on": "--> |phụ thuộc|",
        "default": "-->|",
    }

    def __init__(self):
        self._max_nodes_default = 100
        self._max_depth_default = 3

    async def generate_mermaid(
        self,
        graph_data: Dict[str, Any],
        topic: Optional[str] = None,
        max_nodes: Optional[int] = None,
        max_depth: Optional[int] = None,
        format: str = "mindmap",
    ) -> Dict[str, Any]:
        """
        Generate Mermaid diagram code từ graph data.

        Args:
            graph_data: Dict chứa nodes và edges từ Knowledge Graph
                Format: {
                    "nodes": [{"id": "...", "name": "...", "type": "...", ...}],
                    "edges": [{"source": "...", "target": "...", "label": "...", ...}]
                }
            topic: Topic/root node để bắt đầu extraction (None = lấy toàn bộ)
            max_nodes: Số node tối đa (default: 100)
            max_depth: Độ sâu BFS tối đa (default: 3)
            format: Mermaid format - "mindmap", "flowchart_td", "flowchart_lr"

        Returns:
            Dict với keys:
                - mermaid_code: str chứa Mermaid markup
                - metadata: {total_nodes, total_edges, truncated, format}
        """
        max_nodes = max_nodes or self._max_nodes_default
        max_depth = max_depth or self._max_depth_default

        nodes = graph_data.get("nodes", [])
        edges = graph_data.get("edges", [])

        if not nodes:
            return {
                "mermaid_code": self._empty_diagram(format),
                "metadata": {
                    "total_nodes": 0,
                    "total_edges": 0,
                    "truncated": False,
                    "format": format,
                },
            }

        # Extract subgraph từ topic
        subgraph_nodes, subgraph_edges = self._extract_subgraph(
            nodes, edges, topic, max_nodes, max_depth
        )

        # Convert sang Mermaid syntax
        mermaid_code = self._convert_to_mermaid(
            subgraph_nodes, subgraph_edges, format
        )

        truncated = len(subgraph_nodes) < len(nodes)

        logger.info(
            f"VisualizerAgent: Generated {format} diagram "
            f"({len(subgraph_nodes)} nodes, {len(subgraph_edges)} edges, "
            f"truncated={truncated})"
        )

        return {
            "mermaid_code": mermaid_code,
            "metadata": {
                "total_nodes": len(subgraph_nodes),
                "total_edges": len(subgraph_edges),
                "truncated": truncated,
                "format": format,
            },
        }

    def _extract_subgraph(
        self,
        nodes: List[Dict[str, Any]],
        edges: List[Dict[str, Any]],
        topic: Optional[str],
        max_nodes: int,
        max_depth: int,
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        BFS extraction từ topic root, giới hạn max_nodes và max_depth.

        Nếu topic=None hoặc không tìm thấy topic, lấy toàn bộ graph (giới hạn max_nodes).
        """
        # Build adjacency list
        node_map = {node["id"]: node for node in nodes}
        node_by_name = {node.get("name", node.get("canonical_name", "")): node for node in nodes}

        # Build neighbor map (undirected cho BFS)
        neighbors: Dict[str, set] = {node_id: set() for node_id in node_map}
        edge_map: Dict[Tuple[str, str], List[Dict[str, Any]]] = {}

        for edge in edges:
            source = edge.get("source")
            target = edge.get("target")
            if not source or not target:
                continue

            neighbors.setdefault(source, set())
            neighbors.setdefault(target, set())
            neighbors[source].add(target)
            neighbors[target].add(source)

            edge_map.setdefault((source, target), [])
            edge_map[(source, target)].append(edge)

        # Tìm root node từ topic
        root_id = None
        if topic:
            # Tìm theo ID trước
            if topic in node_map:
                root_id = topic
            # Tìm theo name
            elif topic in node_by_name:
                root_id = node_by_name[topic]["id"]
            else:
                # Fuzzy match: tìm name chứa topic
                for name, node in node_by_name.items():
                    if topic.lower() in name.lower():
                        root_id = node["id"]
                        break

        # Nếu không tìm thấy root, lấy toàn bộ graph
        if not root_id and nodes:
            logger.warning(f"VisualizerAgent: Topic '{topic}' not found, using full graph")
            truncated_nodes = nodes[:max_nodes]
            # Lọc edges chỉ chứa các nodes đã lấy
            truncated_node_ids = {n["id"] for n in truncated_nodes}
            truncated_edges = [
                e for e in edges
                if e.get("source") in truncated_node_ids and e.get("target") in truncated_node_ids
            ]
            return truncated_nodes, truncated_edges

        # BFS từ root
        visited = set()
        visited_edges = set()
        queue = deque([(root_id, 0)])  # (node_id, depth)
        visited.add(root_id)

        while queue and len(visited) < max_nodes:
            current_id, depth = queue.popleft()

            if depth >= max_depth:
                continue

            for neighbor_id in neighbors.get(current_id, []):
                edge_key = (current_id, neighbor_id)
                reverse_edge_key = (neighbor_id, current_id)

                if neighbor_id not in visited and len(visited) < max_nodes:
                    visited.add(neighbor_id)
                    visited_edges.add(edge_key)
                    visited_edges.add(reverse_edge_key)
                    queue.append((neighbor_id, depth + 1))
                elif neighbor_id in visited:
                    visited_edges.add(edge_key)
                    visited_edges.add(reverse_edge_key)

        # Build subgraph
        subgraph_nodes = [node_map[nid] for nid in visited if nid in node_map]
        subgraph_edges = []
        seen_edge_pairs = set()

        for src, tgt in visited_edges:
            pair = tuple(sorted([src, tgt]))
            if pair in seen_edge_pairs:
                continue
            seen_edge_pairs.add(pair)

            for edge in edge_map.get((src, tgt), []) + edge_map.get((tgt, src), []):
                if edge not in subgraph_edges:
                    subgraph_edges.append(edge)

        return subgraph_nodes, subgraph_edges

    def _convert_to_mermaid(
        self,
        nodes: List[Dict[str, Any]],
        edges: List[Dict[str, Any]],
        format: str,
    ) -> str:
        """
        Chuyển đổi nodes/edges thành Mermaid code.

        Supports: mindmap, flowchart_td, flowchart_lr
        """
        if format == "mindmap":
            return self._to_mindmap(nodes, edges)
        elif format in ("flowchart_td", "graph_td"):
            return self._to_flowchart(nodes, edges, direction="TD")
        elif format in ("flowchart_lr", "graph_lr"):
            return self._to_flowchart(nodes, edges, direction="LR")
        else:
            logger.warning(f"VisualizerAgent: Unknown format '{format}', defaulting to mindmap")
            return self._to_mindmap(nodes, edges)

    def _to_mindmap(
        self,
        nodes: List[Dict[str, Any]],
        edges: List[Dict[str, Any]],
    ) -> str:
        """
        Tạo Mermaid mindmap diagram.

        Structure:
        ```mindmap
          root((Root Topic))
            Child 1
              Grandchild
            Child 2
        ```
        """
        if not nodes:
            return self._empty_diagram("mindmap")

        # Tìm root node (node không có edge nào指向 nó, hoặc node đầu tiên)
        has_parent = set()
        for edge in edges:
            target = edge.get("target")
            if target:
                has_parent.add(target)

        root_candidates = [n for n in nodes if n["id"] not in has_parent]
        root = root_candidates[0] if root_candidates else nodes[0]

        # Build children map
        children_map: Dict[str, List[Dict[str, Any]]] = {node["id"]: [] for node in nodes}
        node_map = {node["id"]: node for node in nodes}

        for edge in edges:
            source = edge.get("source")
            target = edge.get("target")
            if source and target and source in node_map and target in node_map:
                children_map[source].append(node_map[target])

        # Render mindmap với BFS tree từ root
        lines = ["mindmap"]
        visited = set()
        self._render_mindmap_node(lines, root, children_map, visited, indent=1)

        # Thêm các node còn lại (nếu có, không nằm trong tree từ root)
        for node in nodes:
            if node["id"] not in visited:
                self._render_mindmap_node(lines, node, children_map, visited, indent=1)

        return "\n".join(lines)

    def _render_mindmap_node(
        self,
        lines: List[str],
        node: Dict[str, Any],
        children_map: Dict[str, List[Dict[str, Any]]],
        visited: set,
        indent: int,
    ):
        """Render mindmap node với recursion cho children."""
        node_id = node["id"]
        if node_id in visited:
            return
        visited.add(node_id)

        # Lấy tên node và escape ký tự đặc biệt
        name = node.get("name", node.get("canonical_name", "Unknown"))
        name = self._escape_mermaid(name)

        # Thêm shape markers tùy type
        entity_type = node.get("entity_type", "default")
        if entity_type == "concept":
            formatted = f"{name}(({name}))"  # Circle
        elif entity_type == "person":
            formatted = f"{name}((({name})))"  # Double circle
        else:
            formatted = name

        lines.append(f"{'  ' * indent}{formatted}")

        # Render children
        for child in children_map.get(node_id, []):
            self._render_mindmap_node(lines, child, children_map, visited, indent + 1)

    def _to_flowchart(
        self,
        nodes: List[Dict[str, Any]],
        edges: List[Dict[str, Any]],
        direction: str = "TD",
    ) -> str:
        """
        Tạo Mermaid flowchart diagram.

        Structure:
        ```flowchart TD
          A[Node A] -->|relation| B[Node B]
        ```
        """
        if not nodes:
            return self._empty_diagram("flowchart", direction)

        lines = [f"graph {direction}"]

        # Tạo node ID mapping (sanitize IDs cho Mermaid)
        node_map = {}
        for i, node in enumerate(nodes):
            mermaid_id = f"N{i}"
            name = node.get("name", node.get("canonical_name", "Unknown"))
            name = self._escape_mermaid(name)
            entity_type = node.get("entity_type", "default")
            color = self.TYPE_COLORS.get(entity_type, self.TYPE_COLORS["default"])

            # Node definition với style
            lines.append(f'  {mermaid_id}["{name}"]')
            lines.append(f"  style {mermaid_id} fill:{color},color:#fff,stroke:#333")
            node_map[node["id"]] = mermaid_id

        # Render edges
        for edge in edges:
            source = edge.get("source")
            target = edge.get("target")
            label = edge.get("label", edge.get("relation_type", ""))

            if source not in node_map or target not in node_map:
                continue

            src_id = node_map[source]
            tgt_id = node_map[target]
            label = self._escape_mermaid(label) if label else ""

            if label:
                lines.append(f"  {src_id} -->|{label}| {tgt_id}")
            else:
                lines.append(f"  {src_id} --> {tgt_id}")

        return "\n".join(lines)

    def _empty_diagram(self, format: str, direction: Optional[str] = None) -> str:
        """Tạo empty Mermaid diagram."""
        if format == "mindmap":
            return "mindmap\n  root((No data available))"
        elif direction:
            return f"graph {direction}\n  empty[(No data available)]"
        else:
            return "graph TD\n  empty[(No data available)]"

    @staticmethod
    def _escape_mermaid(text: str) -> str:
        """Escape ký tự đặc biệt trong Mermaid syntax."""
        if not text:
            return ""
        # Escape quotes và ký tự đặc biệt
        text = text.replace('"', "'")
        text = text.replace("(", "\\u0028")
        text = text.replace(")", "\\u0029")
        text = text.replace("[", "\\u005b")
        text = text.replace("]", "\\u005d")
        text = text.replace("{", "\\u007b")
        text = text.replace("}", "\\u007d")
        return text[:100]  # Truncate tên dài


# Singleton instance
_visualizer_agent: Optional[VisualizerAgent] = None


def get_visualizer_agent() -> VisualizerAgent:
    """Lấy VisualizerAgent singleton instance."""
    global _visualizer_agent
    if _visualizer_agent is None:
        _visualizer_agent = VisualizerAgent()
    return _visualizer_agent
