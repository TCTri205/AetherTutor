# Đặc Tả Kỹ Thuật (Technical Spec)

> **Document Owner:** AetherTutor Team
> **Last Updated:** April 5, 2026
> **Status:** Active (MVP Phase)

---

Tài liệu này cung cấp cái nhìn chi tiết về các thành phần kỹ thuật, hạ tầng và chiến lược triển khai của AetherTutor trong giai đoạn MVP.

---

## 1. Công nghệ Sử dụng (Tech Stack MVP)

### Backend (AI & Logic)

- **Ngôn ngữ:** Python 3.10+
- **Framework:** **FastAPI** (Hiệu năng cao, hỗ trợ asynchronous).
- **AI Library:** **LightRAG** (Graph-based RAG pipeline), LangChain (cho Agent orchestration).
- **Orchestrator:** **Custom State Machine** (MVP). LangGraph là post-MVP (phức tạp hơn mức cần cho R&D).
- **Giao thức:** **Model Context Protocol (MCP)**.
- **Background Worker:** **ARQ** (async Redis queue, fit FastAPI). Celery là post-MVP.

### Frontend (User Experience)

- **Framework:** **React** với TypeScript.
- **Styling:** **Vanilla CSS** (MVP). Tailwind CSS là option nếu cần scale UI post-MVP.
- **Visualization:** Mermaid.js (Sơ đồ), **React Flow** (Graph View, MVP). D3.js là post-MVP nếu cần custom render.

### Lưu trữ (Data)

- **Graph DB (MVP):** **NetworkX** (in-memory graph cho R&D), sau đó upgrade lên **Neo4j** cho production.
- **Vector DB:** **ChromaDB** (embedded cho LightRAG embeddings).
- **Relational DB:** **PostgreSQL** (chạy qua Docker cho cả local dev và production để đảm bảo tính nhất quán).
- **Cache & Queue:** **Redis** (caching + background task queue).

## 2. LightRAG Pipeline & Graph-Based AI Logic

Quy trình xử lý dữ liệu cho mỗi tài liệu người dùng tải lên:

### 2.1 Giai đoạn Ingestion (Nạp liệu)

1. **Extract:** Trích xuất văn bản từ PDF, Web, YouTube.
2. **Entity & Relation Extraction:** Sử dụng LLM để xác định entities (khái niệm, thuật ngữ) và relations (mối quan hệ) từ văn bản.
3. **Entity Resolution:** Chuẩn hóa tên entities (vd: "AI" → "Artificial Intelligence") để tránh trùng lặp.
4. **Graph Construction:** Xây dựng knowledge graph với nodes (entities) và edges (relations).
5. **Embedding & Indexing:** Tạo embeddings cho cả entities và concepts, lưu vào ChromaDB cho retrieval.

### 2.2 Giai đoạn Retrieval (Truy xuất - Dual-Level)

- **Level 1 - Entity Retrieval:** Truy xuất các entities cụ thể liên quan trực tiếp đến query.
- **Level 2 - Concept Retrieval:** Truy xuất các concepts mức cao, kết nối qua graph traversal.
- **Context Assembly:** Kết hợp cả hai levels để tạo context giàu ngữ nghĩa cho LLM.
- **Advantages over Traditional RAG:**
  - ✅ Multi-hop reasoning (trả lời queries cần nhiều bước suy luận)
  - ✅ Relationship-aware (hiểu mối liên hệ giữa concepts)
  - ✅ Incremental updates (thêm document mới mà không rebuild toàn bộ graph)

## 3. Logic Thực thi Phương pháp Học tập

Hệ thống triển khai các kỹ thuật sư phạm thông qua "Prompt Engineering" và "Agent Logic":

- **Logic Feynman:** Agent được cấu hình để "đóng vai" người mới bắt đầu, liên tục đặt câu hỏi "tại sao" cho đến khi người dùng giải thích được bản chất.
- **Logic SM-2:** Thuật toán tính toán `Interval` dựa trên 3 yếu tố:
  - `Ease Factor`: Độ dễ của thẻ.
  - `Repetitions`: Số lần nhớ đúng.
  - `Quality`: Đánh giá chủ quan của người học (0-5).
- **Logic Visualizer:** Tự động sinh cấu trúc Mermaid.js (Mindmap/Flowchart) dựa trên **LightRAG graph structure** (nodes = entities, edges = relations).

## 4. Tối ưu hóa Mô hình (Model Strategy)

AetherTutor sử dụng chiến lược đa mô hình để cân bằng giữa chi phí và hiệu năng. Chi tiết về các mô hình được sử dụng và lộ trình phát triển tính năng có thể xem tại [Roadmap.md](../reports/Roadmap.md).

## 5. Rate Limiting & Token Management

### 5.1 Rate Limiting Strategy

Để bảo vệ hệ thống và đảm bảo công bằng giữa các users, AetherTutor áp dụng rate limiting:

```python
from fastapi import Request, HTTPException
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

# Rate limits per subscription tier
RATE_LIMITS = {
    "free": {
        "requests_per_minute": 10,
        "documents_per_day": 5,
        "tokens_per_day": 50_000,
        "api_calls_per_day": 1_000,
    },
    "pro": {
        "requests_per_minute": 60,
        "documents_per_day": 50,
        "tokens_per_day": 500_000,
        "api_calls_per_day": 10_000,
    },
    "enterprise": {
        "requests_per_minute": 300,
        "documents_per_day": -1,  # Unlimited
        "tokens_per_day": -1,
        "api_calls_per_day": -1,
    }
}

@limiter.limit("10/minute")
@router.post("/api/v1/chat/socratic")
async def socratic_chat(request: Request, payload: ChatPayload):
    # Check user quota
    user_quota = await get_user_quota(payload.user_id)
    if not has_quota_remaining(user_quota):
        raise HTTPException(
            status_code=429,
            detail="Daily quota exceeded. Upgrade your plan for more requests."
        )
    
    # Process request
    response = await process_chat_message(payload)
    
    # Log token usage
    await log_api_usage(
        user_id=payload.user_id,
        endpoint="/chat/socratic",
        tokens_consumed=response.token_count
    )
    
    return response
```

### 5.2 Token Usage Tracking

```sql
-- View: Daily token usage per user
CREATE VIEW daily_token_usage AS
SELECT 
    user_id,
    DATE(created_at) as usage_date,
    COUNT(*) as total_requests,
    SUM(tokens_consumed) as total_tokens,
    ARRAY_AGG(DISTINCT endpoint) as endpoints_used
FROM api_usage_logs
GROUP BY user_id, DATE(created_at);

-- Query remaining quota
SELECT 
    ql.daily_tokens,
    COALESCE(du.total_tokens, 0) as used_tokens,
    ql.daily_tokens - COALESCE(du.total_tokens, 0) as remaining_tokens
FROM user_quota_limits ql
LEFT JOIN daily_token_usage du 
    ON ql.user_id = du.user_id 
    AND du.usage_date = CURRENT_DATE
WHERE ql.user_id = :user_id;
```

### 5.3 Cost Optimization Strategies

| Strategy | Description | Savings |
|---|---|---|
| **Caching** | Cache repeated queries (Redis, 7-day TTL) | 30-40% |
| **Model Routing** | Use cheaper models for simple tasks (GPT-3.5 vs GPT-4) | 50-70% |
| **Prompt Optimization** | Reduce prompt token count via templates | 10-20% |
| **Batch Processing** | Batch embeddings API calls | 20-30% |
| **Fallback to Local** | Use Ollama for non-critical tasks | 100% (after setup) |

## 6. Data Isolation & Security

### 6.1 Multi-Tenancy Isolation

Mọi thành phần lưu trữ đều phải implement user isolation:

**PostgreSQL:**
- Row-Level Security (RLS) policies
- Mọi table đều có `user_id` FK
- Application-level filtering middleware

**ChromaDB:**
```python
# Correct: Filter by user_id
results = collection.query(
    query_embeddings=[embedding],
    where={"user_id": current_user_id},  # REQUIRED
    n_results=top_k
)

# Wrong: No filter (security risk!)
results = collection.query(
    query_embeddings=[embedding],
    n_results=top_k
)
```

**NetworkX Graph:**
```python
class UserIsolatedGraph:
    """Graph wrapper that enforces user isolation."""
    
    def __init__(self, graph: nx.Graph, user_id: UUID):
        self.graph = graph
        self.user_id = user_id
    
    def nodes(self, data=False):
        """Only return nodes belonging to current user."""
        all_nodes = self.graph.nodes(data=True)
        return [
            (nid, ndata) for nid, ndata in all_nodes
            if ndata.get('user_id') == str(self.user_id)
        ]
    
    def get_subgraph(self):
        """Get user's subgraph."""
        user_nodes = [n for n, _ in self.nodes()]
        return self.graph.subgraph(user_nodes)
```

### 6.2 Data Encryption

| Data Type | Encryption | Storage |
|---|---|---|
| Passwords | bcrypt hashing | PostgreSQL |
| API Keys | AES-256 encrypted | Environment variables / Vault |
| User Documents | At-rest encryption | S3/local with LUKS |
| Embeddings | Not encrypted (metadata filtered) | ChromaDB |
| Chat History | Encrypted at rest | PostgreSQL |

### 6.3 Audit Logging

```python
import logging
from datetime import datetime

audit_logger = logging.getLogger('audit')

async def log_security_event(
    event_type: str,
    user_id: Optional[UUID],
    details: dict,
    severity: str = "INFO"
):
    """Log security-relevant events."""
    audit_logger.info({
        "timestamp": datetime.utcnow().isoformat(),
        "event_type": event_type,
        "user_id": str(user_id) if user_id else None,
        "severity": severity,
        "details": details,
    })

# Events to log:
# - Failed login attempts (>3 = brute force alert)
# - Quota exceeded
# - Unauthorized access attempts
# - Data export requests
# - Account deletion requests
```

## 7. API Endpoints Cốt lõi

Xem chi tiết danh sách API và mô tả tham số tại [API_Specifications.md](API_Specifications.md).

---
> [!IMPORTANT]
> Toàn bộ hệ thống được thiết kế theo tư duy mã nguồn mở, hỗ trợ chạy Local LLMs để bảo mật dữ liệu tri thức cá nhân.

---
© 2026 AetherTutor Team. Last updated: April 5, 2026
