"""
GraphBuilder - Knowledge Graph Construction & Analysis

Service chịu trách nhiệm xây dựng, phân tích và quản lý knowledge graph.
Sử dụng NetworkX làm core graph representation và StorageProvider
để persist/load graph data.

Features:
- Build nx.MultiDiGraph từ entities và relations
- Persist graph ra disk (GraphML/JSON) qua StorageProvider
- Load graph từ disk
- Tính centrality scores (degree, betweenness)
- Multi-hop neighbor traversal (BFS)
- Community detection
"""

import copy
import json
from typing import Dict, List, Any, Optional
from datetime import datetime

import networkx as nx
from loguru import logger

from app.core.storage_provider import get_storage_provider


class GraphBuilder:
    """
    Builder và analyzer cho knowledge graph.
    
    Usage:
        builder = GraphBuilder()
        await builder.add_entities_and_relations(entities, relations)
        await builder.persist_graph(document_id)
        
        # Analysis
        centrality = await builder.get_centrality_scores(document_id)
        neighbors = await builder.get_multi_hop_neighbors(entity_name, max_depth=2)
    """
    
    def __init__(self):
        self.graph: nx.MultiDiGraph = nx.MultiDiGraph()
        self._storage = get_storage_provider()
        self._centrality_cache: Dict[str, Any] = {}
    
    async def add_entities_and_relations(
        self,
        entities: List[Dict[str, Any]],
        relations: List[Dict[str, Any]],
        document_id: Optional[str] = None,
    ) -> None:
        """
        Xây dựng hoặc cập nhật Knowledge Graph từ extracted entities.
        
        Args:
            entities: List of entity dicts với keys:
                - canonical_name: str (unique identifier)
                - entity_type: str (concept, person, place, ...)
                - description: str
                - confidence: float (0-1)
            relations: List of relation dicts với keys:
                - source_entity: str (canonical_name)
                - target_entity: str (canonical_name)
                - relation_type: str
                - description: str
            document_id: Optional document ID cho metadata
        """
        logger.debug(
            f"GraphBuilder: Adding {len(entities)} entities "
            f"và {len(relations)} relations"
        )
        
        # Bước 1: Thêm entities làm nodes
        for entity in entities:
            canonical_name = entity.get("canonical_name")
            if not canonical_name:
                logger.warning(f"Entity không có canonical_name, skip: {entity}")
                continue
            
            # Thêm node với attributes
            self.graph.add_node(
                canonical_name,
                entity_type=entity.get("entity_type", "unknown"),
                description=entity.get("description", ""),
                confidence=entity.get("confidence", 0.5),
                document_id=document_id,
                created_at=datetime.utcnow().isoformat(),
            )
        
        # Bước 2: Thêm relations làm edges
        for relation in relations:
            source = relation.get("source_entity")
            target = relation.get("target_entity")
            
            if not source or not target:
                logger.warning(f"Relation thiếu source/target, skip: {relation}")
                continue
            
            # Kiểm tra nodes tồn tại (tự động tạo nếu chưa có)
            if not self.graph.has_node(source):
                logger.debug(f"Auto-creating source node: {source}")
                self.graph.add_node(source, entity_type="inferred", description="")
            
            if not self.graph.has_node(target):
                logger.debug(f"Auto-creating target node: {target}")
                self.graph.add_node(target, entity_type="inferred", description="")
            
            # Thêm edge với metadata
            self.graph.add_edge(
                source,
                target,
                relation_type=relation.get("relation_type", "related_to"),
                description=relation.get("description", ""),
                document_id=document_id,
                created_at=datetime.utcnow().isoformat(),
            )
        
        # Invalidate centrality cache sau khi update
        self._centrality_cache.clear()
        
        logger.info(
            f"GraphBuilder: Graph now has "
            f"{self.graph.number_of_nodes()} nodes, "
            f"{self.graph.number_of_edges()} edges"
        )
    
    async def persist_graph(self, document_id: str) -> bool:
        """
        Lưu graph ra disk dưới dạng GraphML và JSON.
        
        Args:
            document_id: Document ID để tạo storage key
            
        Returns:
            True nếu lưu thành công
        """
        if self.graph.number_of_nodes() == 0:
            logger.warning("Graph rỗng, không persist")
            return False
        
        try:
            # GraphML không support None values → cần filter attributes
            export_graph = copy.deepcopy(self.graph)
            for node in export_graph.nodes(data=True):
                node_name = node[0]
                attrs = node[1]
                # Remove None values
                none_keys = [k for k, v in attrs.items() if v is None]
                for k in none_keys:
                    del export_graph.nodes[node_name][k]
            for source, target, key, attrs in export_graph.edges(data=True, keys=True):
                none_keys = [k for k, v in attrs.items() if v is None]
                for k in none_keys:
                    del export_graph[source][target][key][k]

            # Export GraphML (dễ import lại vào NetworkX)
            # Note: nx.generate_graphml returns generator in NetworkX 3.x
            graphml_data = "".join(nx.generate_graphml(export_graph))
            graphml_bytes = graphml_data.encode("utf-8")
            
            graphml_key = f"graphs/{document_id}/knowledge_graph.graphml"
            await self._storage.save(graphml_key, graphml_bytes)
            
            # Export JSON (dễ đọc bởi frontend/other services)
            json_data = self._graph_to_dict()
            json_bytes = json.dumps(json_data, ensure_ascii=False).encode("utf-8")
            
            json_key = f"graphs/{document_id}/knowledge_graph.json"
            await self._storage.save(json_key, json_bytes)
            
            logger.info(
                f"GraphBuilder persisted graph for document {document_id}: "
                f"{self.graph.number_of_nodes()} nodes, {self.graph.number_of_edges()} edges"
            )
            return True
            
        except Exception as e:
            logger.error(f"GraphBuilder persist error: {e}", exc_info=True)
            return False
    
    async def load_graph(self, document_id: str) -> bool:
        """
        Load graph từ disk.
        
        Args:
            document_id: Document ID để tạo storage key
            
        Returns:
            True nếu load thành công
        """
        try:
            graphml_key = f"graphs/{document_id}/knowledge_graph.graphml"
            graphml_bytes = await self._storage.load(graphml_key)
            
            if graphml_bytes is None:
                logger.debug(f"No graph found for document {document_id}")
                return False
            
            graphml_str = graphml_bytes.decode("utf-8")
            self.graph = nx.parse_graphml(graphml_str)
            
            logger.info(
                f"GraphBuilder loaded graph for document {document_id}: "
                f"{self.graph.number_of_nodes()} nodes, {self.graph.number_of_edges()} edges"
            )
            return True
            
        except Exception as e:
            logger.error(f"GraphBuilder load error: {e}", exc_info=True)
            return False
    
    async def get_centrality_scores(
        self,
        document_id: Optional[str] = None,
    ) -> Dict[str, Dict[str, float]]:
        """
        Tính centrality scores cho tất cả nodes trong graph.
        
        Centrality measures:
        - degree_centrality: Số lượng connections (popularity)
        - betweenness_centrality: Số lần node nằm trên shortest path (bridge)
        - closeness_centrality: Khoảng cách trung bình tới các nodes khác
        
        Args:
            document_id: Optional, filter nodes theo document_id
            
        Returns:
            Dict mapping entity_name -> {
                "degree_centrality": float,
                "betweenness_centrality": float,
                "closeness_centrality": float,
            }
        """
        # Check cache
        cache_key = document_id or "all"
        if cache_key in self._centrality_cache:
            return self._centrality_cache[cache_key]
        
        if self.graph.number_of_nodes() == 0:
            return {}
        
        try:
            # Tính centrality metrics
            degree = nx.degree_centrality(self.graph)
            betweenness = nx.betweenness_centrality(self.graph)
            closeness = nx.closeness_centrality(self.graph)
            
            # Combine vào dict
            scores = {}
            for node in self.graph.nodes():
                # Filter theo document_id nếu cần
                if document_id:
                    node_doc = self.graph.nodes[node].get("document_id")
                    if node_doc != document_id:
                        continue
                
                scores[node] = {
                    "degree_centrality": degree.get(node, 0.0),
                    "betweenness_centrality": betweenness.get(node, 0.0),
                    "closeness_centrality": closeness.get(node, 0.0),
                }
            
            # Cache kết quả
            self._centrality_cache[cache_key] = scores
            
            logger.debug(f"Centrality scores calculated for {len(scores)} nodes")
            return scores
            
        except Exception as e:
            logger.error(f"Centrality calculation error: {e}", exc_info=True)
            return {}
    
    async def get_multi_hop_neighbors(
        self,
        entity_name: str,
        max_depth: int = 2,
        document_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        BFS traversal để tìm neighbors trong max_depth hops.
        
        Args:
            entity_name: Entity canonical_name để bắt đầu traversal
            max_depth: Số hops tối đa (default: 2)
            document_id: Optional, filter neighbors theo document_id
            
        Returns:
            {
                "entity": entity_name,
                "neighbors": {
                    1: [list của neighbors 1 hop],
                    2: [list của neighbors 2 hops],
                },
                "subgraph_nodes": [tất cả nodes trong subgraph],
                "subgraph_edges": [tất cả edges trong subgraph],
            }
        """
        if not self.graph.has_node(entity_name):
            logger.warning(f"Entity không tồn tại trong graph: {entity_name}")
            return {
                "entity": entity_name,
                "neighbors": {},
                "subgraph_nodes": [],
                "subgraph_edges": [],
            }
        
        # BFS traversal
        neighbors_by_depth: Dict[int, List[str]] = {}
        visited = {entity_name}
        current_level = {entity_name}
        
        for depth in range(1, max_depth + 1):
            next_level = set()
            
            for node in current_level:
                for neighbor in self.graph.neighbors(node):
                    if neighbor not in visited:
                        # Filter theo document_id nếu cần
                        if document_id:
                            neighbor_doc = self.graph.nodes[neighbor].get(
                                "document_id"
                            )
                            if neighbor_doc != document_id:
                                continue
                        
                        next_level.add(neighbor)
                        visited.add(neighbor)
            
            if next_level:
                neighbors_by_depth[depth] = list(next_level)
            
            current_level = next_level
            if not current_level:
                break
        
        # Thu thập subgraph edges (duyệt qua edges 1 lần, tránh duplicate)
        subgraph_edges = []
        seen_edge_pairs = set()
        for source, target, edge_key, edge_data in self.graph.edges(data=True, keys=True):
            if source in visited and target in visited:
                edge_pair_id = (source, target, edge_key)
                if edge_pair_id not in seen_edge_pairs:
                    seen_edge_pairs.add(edge_pair_id)
                    subgraph_edges.append({
                        "source": source,
                        "target": target,
                        "relation_type": edge_data.get("relation_type", "related_to"),
                        "description": edge_data.get("description", ""),
                    })
        
        return {
            "entity": entity_name,
            "neighbors": neighbors_by_depth,
            "subgraph_nodes": list(visited),
            "subgraph_edges": subgraph_edges,
        }
    
    async def detect_communities(
        self,
        document_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Phát hiện communities trong graph dùng greedy modularity.
        
        Returns:
            List của communities, mỗi community có:
                - "community_id": int
                - "nodes": list của entity names
                - "size": number of nodes
        """
        if self.graph.number_of_nodes() < 2:
            return []
        
        try:
            # Chuyển MultiDiGraph sang Graph cho community detection
            simple_graph = nx.Graph(self.graph)
            
            # Filter theo document_id nếu cần
            if document_id:
                nodes_to_keep = [
                    node for node in simple_graph.nodes()
                    if simple_graph.nodes[node].get("document_id") == document_id
                ]
                simple_graph = simple_graph.subgraph(nodes_to_keep)
            
            # Greedy modularity communities
            from networkx.algorithms.community import greedy_modularity_communities
            
            communities = greedy_modularity_communities(simple_graph)
            
            result = []
            for i, community in enumerate(communities):
                result.append({
                    "community_id": i,
                    "nodes": list(community),
                    "size": len(community),
                })
            
            logger.info(f"Detected {len(result)} communities")
            return result
            
        except Exception as e:
            logger.error(f"Community detection error: {e}", exc_info=True)
            return []
    
    def get_graph_stats(self) -> Dict[str, Any]:
        """
        Lấy thống kê tổng quan về graph.
        
        Returns:
            Dict với các metrics:
                - node_count
                - edge_count
                - density
                - avg_degree
                - is_connected
                - num_components
        """
        if self.graph.number_of_nodes() == 0:
            return {
                "node_count": 0,
                "edge_count": 0,
                "density": 0.0,
                "avg_degree": 0.0,
                "is_connected": False,
                "num_components": 0,
            }
        
        # Tính các metrics
        density = nx.density(self.graph)
        total_degree = sum(d for _, d in self.graph.degree())
        avg_degree = total_degree / self.graph.number_of_nodes()
        
        # Weakly connected components (cho directed graph)
        num_components = nx.number_weakly_connected_components(self.graph)
        is_connected = num_components == 1
        
        return {
            "node_count": self.graph.number_of_nodes(),
            "edge_count": self.graph.number_of_edges(),
            "density": round(density, 4),
            "avg_degree": round(avg_degree, 2),
            "is_connected": is_connected,
            "num_components": num_components,
        }
    
    def _graph_to_dict(self) -> Dict[str, Any]:
        """Convert graph thành dict để export JSON."""
        data = {
            "nodes": [],
            "edges": [],
            "metadata": {
                "created_at": datetime.utcnow().isoformat(),
                "node_count": self.graph.number_of_nodes(),
                "edge_count": self.graph.number_of_edges(),
            },
        }
        
        # Export nodes
        for node, node_data in self.graph.nodes(data=True):
            data["nodes"].append({
                "id": node,
                **node_data,
            })
        
        # Export edges
        for source, target, edge_key, edge_data in self.graph.edges(data=True, keys=True):
            data["edges"].append({
                "source": source,
                "target": target,
                "key": edge_key,
                **edge_data,
            })
        
        return data
    
    def get_graph(self) -> nx.MultiDiGraph:
        """Trả về NetworkX graph object."""
        return self.graph
    
    def clear(self) -> None:
        """Xóa toàn bộ graph trong memory."""
        self.graph.clear()
        self._centrality_cache.clear()
        logger.debug("GraphBuilder cleared")


# Singleton instance
_graph_builder: Optional[GraphBuilder] = None


def get_graph_builder() -> GraphBuilder:
    """Lấy GraphBuilder singleton instance."""
    global _graph_builder
    if _graph_builder is None:
        _graph_builder = GraphBuilder()
    return _graph_builder


def reset_graph_builder():
    """Reset singleton (chỉ dùng cho testing)."""
    global _graph_builder
    _graph_builder = None
