# Deployment Architecture (Future Plan)

> [!NOTE]
> **LightRAG Integration Note:**
> Tài liệu này phác thảo chiến lược triển khai cho AetherTutor với LightRAG làm core technology.
> Khi chuyển từ MVP (NetworkX in-memory) sang Production, cần upgrade lên **Neo4j** cho graph storage
> để đảm bảo performance và scalability cho knowledge graph queries.

Tài liệu này phác thảo chiến lược triển khai lâu dài cho AetherTutor khi sẵn sàng đưa vào Production.

---

## 1. Containerization

- **Backend:** Dockerized FastAPI service.
- **Frontend:** Static build deployed through NGINX.
- **Agent Workers:** Celery hoặc RQ cho các tác vụ tốn thời gian (Entity Extraction, Graph Construction, Embedding Generation).
- **LightRAG Workers:** Dedicated workers cho graph traversal và multi-hop retrieval operations.

## 2. Infrastructure (AWS/GCP)

- **Database:** PostgreSQL (Managed service) - User data, metadata.
- **Graph Database:** **Neo4j** (Production) - LightRAG knowledge graph (upgrade từ NetworkX MVP).
- **Vector Storage:** ChromaDB/Qdrant (Clustered) - Entity & concept embeddings.
- **Caching:** Redis - Retrieval results, graph queries, session data.
- **Orchestration:** Kubernetes (EKS/GKE) cho việc scale tự động.

## 3. LightRAG-Specific Infrastructure

### 3.1 Graph Storage Strategy

| Stage | Technology | Scale | Use Case |
|---|---|---|---|
| **MVP/Development** | NetworkX (in-memory) | < 100 docs | Testing, single-user |
| **Staging** | Neo4j Community | < 10K entities | Integration testing |
| **Production** | Neo4j Enterprise / AuraDB | 100K+ entities | Multi-user, high-concurrency |

### 3.2 Performance Requirements

| Operation | Target | Notes |
|---|---|---|
| Entity Extraction | < 5s per chunk | LLM-dependent |
| Graph Construction | < 10s per doc | NetworkX → Neo4j sync |
| Dual-Level Retrieval | < 500ms | Cached: < 100ms |
| Multi-hop Query | < 1s | Max depth: 3 |
| Incremental Update | < 5% of full rebuild | Add new doc |

### 3.3 Scaling Considerations

**Graph Partitioning:**
- Partition by user_id (multi-tenant isolation)
- Shard large graphs by document clusters
- Implement graph caching per partition

**Embedding Strategy:**
- Batch embedding generation for new entities
- Approximate Nearest Neighbor (ANN) for large-scale retrieval
- Cache frequently accessed entity embeddings

## 4. High Availability

- Triển khai đa vùng (Multi-AZ) để đảm bảo độ tin cậy.
- CDNs (Cloudflare) cho việc phân phối Frontend.
- Neo4j Causal Cluster cho graph high availability.

## 5. Monitoring & Observability (LightRAG-Specific)

### 5.1 Key Metrics to Track

| Metric | Alert Threshold | Purpose |
|---|---|---|
| Graph Size (entities) | > 50K per user | Performance degradation |
| Retrieval Latency | > 1s | User experience |
| Entity Extraction Quality | < 75% confidence | LLM prompt tuning |
| Cache Hit Rate | < 60% | Caching strategy effectiveness |
| Graph Density | > 0.1 or < 0.001 | Data quality indicator |

### 5.2 Observability Stack

- **Prometheus + Grafana:** Metrics dashboard
- **ELK Stack:** Log aggregation and analysis
- **Jaeger:** Distributed tracing (agent workflows)
- **Neo4j Bloom:** Graph visualization and debugging

---
> [!NOTE]
> Giai đoạn hiện tại (R&D) chỉ yêu cầu chạy thông qua Docker Compose đơn giản trên môi trường Local.
> LightRAG MVP sử dụng NetworkX + ChromaDB embedded - không cần external dependencies.
> Production upgrade lên Neo4j sẽ được thực hiện khi có > 100 active users.
