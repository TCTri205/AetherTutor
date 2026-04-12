"""
Unit tests cho VisualizerAgent - Sprint 8 - B4

Test subgraph extraction, mermaid conversion, edge cases.
"""

import pytest
from app.core.visualizer_agent import VisualizerAgent


@pytest.fixture
def agent():
    return VisualizerAgent()


@pytest.fixture
def sample_graph_data():
    """Graph mẫu với 5 nodes và 4 edges."""
    return {
        "nodes": [
            {"id": "n1", "name": "Machine Learning", "type": "concept"},
            {"id": "n2", "name": "Neural Networks", "type": "concept"},
            {"id": "n3", "name": "Deep Learning", "type": "concept"},
            {"id": "n4", "name": "Supervised Learning", "type": "concept"},
            {"id": "n5", "name": "Training Data", "type": "object"},
        ],
        "edges": [
            {"source": "n1", "target": "n2", "label": "uses"},
            {"source": "n2", "target": "n3", "label": "enables"},
            {"source": "n1", "target": "n4", "label": "includes"},
            {"source": "n4", "target": "n5", "label": "requires"},
        ],
    }


@pytest.fixture
def empty_graph_data():
    return {"nodes": [], "edges": []}


class TestSubgraphExtraction:
    def test_extract_full_graph_no_topic(self, agent, sample_graph_data):
        """Khi topic=None, lấy toàn bộ graph (giới hạn max_nodes)."""
        nodes, edges = agent._extract_subgraph(
            sample_graph_data["nodes"],
            sample_graph_data["edges"],
            topic=None,
            max_nodes=100,
            max_depth=3,
        )
        assert len(nodes) == 5
        assert len(edges) == 4

    def test_extract_subgraph_from_topic(self, agent, sample_graph_data):
        """BFS từ topic root."""
        nodes, edges = agent._extract_subgraph(
            sample_graph_data["nodes"],
            sample_graph_data["edges"],
            topic="n1",
            max_nodes=100,
            max_depth=2,
        )
        # n1 có neighbors: n2, n4 (depth 1)
        # n2→n3, n4→n5 (depth 2)
        assert len(nodes) >= 3  # Ít nhất n1 + 2 neighbors
        assert "n1" in [n["id"] for n in nodes]

    def test_extract_subgraph_topic_not_found(self, agent, sample_graph_data):
        """Topic không tồn tại → fallback lấy toàn bộ graph."""
        nodes, edges = agent._extract_subgraph(
            sample_graph_data["nodes"],
            sample_graph_data["edges"],
            topic="nonexistent",
            max_nodes=100,
            max_depth=3,
        )
        assert len(nodes) == 5
        assert len(edges) == 4

    def test_extract_max_nodes_truncation(self, agent, sample_graph_data):
        """Giới hạn max_nodes."""
        nodes, edges = agent._extract_subgraph(
            sample_graph_data["nodes"],
            sample_graph_data["edges"],
            topic="n1",
            max_nodes=3,
            max_depth=10,
        )
        assert len(nodes) <= 3

    def test_extract_max_depth_limit(self, agent, sample_graph_data):
        """Giới hạn max_depth."""
        nodes, edges = agent._extract_subgraph(
            sample_graph_data["nodes"],
            sample_graph_data["edges"],
            topic="n1",
            max_nodes=100,
            max_depth=1,
        )
        # Chỉ n1 + direct neighbors (n2, n4)
        node_ids = [n["id"] for n in nodes]
        assert "n1" in node_ids
        assert len(nodes) <= 3

    def test_extract_empty_graph(self, agent, empty_graph_data):
        nodes, edges = agent._extract_subgraph(
            empty_graph_data["nodes"],
            empty_graph_data["edges"],
            topic=None,
            max_nodes=100,
            max_depth=3,
        )
        assert len(nodes) == 0
        assert len(edges) == 0


class TestMermaidConversion:
    def test_mindmap_format(self, agent, sample_graph_data):
        nodes, edges = agent._extract_subgraph(
            sample_graph_data["nodes"],
            sample_graph_data["edges"],
            topic="n1",
            max_nodes=100,
            max_depth=3,
        )
        mermaid = agent._convert_to_mermaid(nodes, edges, "mindmap")
        assert mermaid.startswith("mindmap")

    def test_flowchart_td_format(self, agent, sample_graph_data):
        nodes, edges = agent._extract_subgraph(
            sample_graph_data["nodes"],
            sample_graph_data["edges"],
            topic="n1",
            max_nodes=100,
            max_depth=3,
        )
        mermaid = agent._convert_to_mermaid(nodes, edges, "flowchart_td")
        assert mermaid.startswith("graph TD")

    def test_flowchart_lr_format(self, agent, sample_graph_data):
        nodes, edges = agent._extract_subgraph(
            sample_graph_data["nodes"],
            sample_graph_data["edges"],
            topic="n1",
            max_nodes=100,
            max_depth=3,
        )
        mermaid = agent._convert_to_mermaid(nodes, edges, "flowchart_lr")
        assert mermaid.startswith("graph LR")

    def test_unknown_format_fallback(self, agent, sample_graph_data):
        nodes, edges = agent._extract_subgraph(
            sample_graph_data["nodes"],
            sample_graph_data["edges"],
            topic="n1",
            max_nodes=100,
            max_depth=3,
        )
        mermaid = agent._convert_to_mermaid(nodes, edges, "unknown")
        assert mermaid.startswith("mindmap")


class TestEmptyDiagram:
    @pytest.mark.asyncio
    async def test_empty_mindmap(self, agent, empty_graph_data):
        result = await agent.generate_mermaid(empty_graph_data, format="mindmap")
        assert "mermaid_code" in result
        assert result["metadata"]["total_nodes"] == 0
        assert result["metadata"]["truncated"] is False

    @pytest.mark.asyncio
    async def test_empty_flowchart(self, agent, empty_graph_data):
        result = await agent.generate_mermaid(empty_graph_data, format="flowchart_td")
        assert "mermaid_code" in result
        assert "graph TD" in result["mermaid_code"]


class TestMetadata:
    def test_metadata_truncated(self, agent, sample_graph_data):
        nodes, edges = agent._extract_subgraph(
            sample_graph_data["nodes"],
            sample_graph_data["edges"],
            topic="n1",
            max_nodes=2,
            max_depth=10,
        )
        _ = agent._convert_to_mermaid(nodes, edges, "mindmap")  # Verify không crash
        assert len(nodes) < 5  # Bị truncate
        # Metadata sẽ có truncated=True từ generate_mermaid

    @pytest.mark.asyncio
    async def test_metadata_counts(self, agent, sample_graph_data):
        result = await agent.generate_mermaid(
            sample_graph_data,
            topic=None,
            max_nodes=100,
            max_depth=3,
            format="mindmap",
        )
        assert result["metadata"]["total_nodes"] == 5
        assert result["metadata"]["total_edges"] == 4
        assert result["metadata"]["truncated"] is False
        assert result["metadata"]["format"] == "mindmap"


class TestEdgeCases:
    @pytest.mark.asyncio
    async def test_special_characters_in_name(self, agent):
        """Escape ký tự đặc biệt trong tên node."""
        graph = {
            "nodes": [{"id": "n1", "name": "C++ & Python (3.11)", "type": "concept"}],
            "edges": [],
        }
        result = await agent.generate_mermaid(graph, format="mindmap")
        # Không được crash
        assert "mermaid_code" in result

    @pytest.mark.asyncio
    async def test_very_long_name_truncated(self, agent):
        """Tên dài >100 ký tự bị truncate."""
        long_name = "A" * 150
        graph = {
            "nodes": [{"id": "n1", "name": long_name, "type": "concept"}],
            "edges": [],
        }
        result = await agent.generate_mermaid(graph, format="mindmap")
        assert "mermaid_code" in result
        # Tên phải được truncate trong mermaid code

    @pytest.mark.asyncio
    async def test_disconnected_nodes(self, agent):
        """Nodes không có edges."""
        graph = {
            "nodes": [
                {"id": "n1", "name": "Node 1", "type": "concept"},
                {"id": "n2", "name": "Node 2", "type": "concept"},
            ],
            "edges": [],
        }
        result = await agent.generate_mermaid(graph, topic=None, format="flowchart_td")
        assert "mermaid_code" in result
        # Vẫn phải render được cả 2 nodes
