# API Specifications (MVP Core)

> **Document Owner:** AetherTutor Team
> **Last Updated:** April 5, 2026
> **Status:** Active (MVP Phase)

---

Tài liệu này định nghĩa chi tiết các API endpoints cốt lõi cho giai đoạn MVP của AetherTutor. Toàn bộ đặc tả chi tiết (OpenAPI 3.0) có thể tham khảo tại [API_Full_Spec.md](future_ops/API_Full_Spec.md).

---

## 1. Core Endpoints

### 1.1 Ingestion & Processing

| Endpoint | Method | Mô tả |
| :--- | :--- | :--- |
| `/api/v1/documents/process` | POST | Tải lên PDF/Link và bắt đầu quy trình **LightRAG Entity Extraction & Graph Construction**. |
| `/api/v1/documents/{id}/status` | GET | Kiểm tra trạng thái xử lý tài liệu. |
| `/api/v1/documents/{id}/graph` | GET | Xem knowledge graph của document (entities & relations). |

### 1.2 LightRAG Graph Querying

| Endpoint | Method | Mô tả |
| :--- | :--- | :--- |
| `/api/v1/graph/query` | POST | Truy vấn knowledge graph với dual-level retrieval (entities + concepts). |
| `/api/v1/graph/entities/{entity_id}` | GET | Lấy thông tin chi tiết của một entity và neighbors. |
| `/api/v1/graph/relations` | GET | Lấy danh sách relations giữa các entities. |
| `/api/v1/graph/subgraph` | POST | Extract subgraph xung quanh một topic (cho visualization). |
| `/api/v1/graph/stats` | GET | Thống kê graph (total entities, relations, density). |

### 1.3 Learning Agents (MVP)

| Endpoint | Method | Mô tả |
| :--- | :--- | :--- |
| `/api/v1/chat/socratic` | POST | Gửi tin nhắn đến Socratic Tutor Agent (Feynman Method) với **graph-aware context**. |
| `/api/v1/flashcards/generate` | POST | Tự động tạo flashcard từ **graph entities** với SM-2 scheduling. |
| `/api/v1/flashcards/due` | GET | Lấy danh sách flashcard cần ôn tập (SM-2). |
| `/api/v1/flashcards/{id}/review` | POST | Cập nhật kết quả ôn tập flashcard (SM-2 algorithm). |
| `/api/v1/quiz/generate` | POST | Tự động tạo câu hỏi kiểm tra từ **graph entities & relations**. |
| `/api/v1/quiz/{quiz_id}/submit` | POST | Nộp bài quiz và chấm điểm. |
| `/api/v1/notes` | POST | Tạo ghi chú dạng thẻ (Atomic note) mới với **backlink suggestion**. |
| `/api/v1/notes/{id}` | GET | Lấy ghi chú với backlinks và linked entities. |
| `/api/v1/dashboard` | GET | Lấy overview stats cho Dashboard (stats, due cards, recent docs, graph preview). |
| `/api/v1/settings/model` | POST | Thay đổi LLM mode (Local ↔ Cloud) và model configuration. |

---

## 1b. Post-MVP Endpoints (Không build trong MVP)

> [!WARNING]
> Các endpoint dưới đây **không thuộc MVP scope**. Tham khảo [MVP_Implementation_Plan.md#2-phạm-vi-mvp-mvp-scope](../plans/MVP_Implementation_Plan.md#2-phạm-vi-mvp-mvp-scope) để biết chi tiết.

### Post-MVP: Authentication & Multi-Tenancy

| Endpoint | Method | Mô tả |
| :--- | :--- | :--- |
| `/api/v1/auth/register` | POST | Đăng ký tài khoản mới. |
| `/api/v1/auth/login` | POST | Đăng nhập (JWT). |
| `/api/v1/auth/refresh` | POST | Refresh access token. |
| `/api/v1/users/me` | GET | Lấy thông tin user hiện tại. |

### Post-MVP: Media Pipeline

| Endpoint | Method | Mô tả |
| :--- | :--- | :--- |
| `/api/v1/documents/process/youtube` | POST | Xử lý video YouTube thành micro-learning. |
| `/api/v1/documents/process/audio` | POST | Xử lý audio file thành text + notes. |

### Post-MVP: Advanced Features

| Endpoint | Method | Mô tả |
| :--- | :--- | :--- |
| `/api/v1/visualize/graph` | POST | Yêu cầu sinh mã Mermaid từ **LightRAG knowledge graph**. |
| `/api/v1/payments/subscribe` | POST | Đăng ký subscription tier. |
| `/api/v1/analytics/usage` | GET | Lấy thống kê API usage và quota. |

---

## 2. Authentication & Headers

> [!NOTE]
> **MVP (Local mode):** Không yêu cầu authentication. Hệ thống chạy single-user local, không có JWT. Header `Authorization` chỉ áp dụng từ **Post-MVP Phase** (Week 17+).

- **Auth (Post-MVP):** JWT Bearer Token.
- **Protocol:** Mọi giao tiếp giữa các Agent backend sử dụng **Model Context Protocol (MCP)**.
- **Headers (Post-MVP):**

```http
Authorization: Bearer <token>
X-Learning-Profile: System/Technical/Creative
```

---

## 3. LightRAG-Specific Endpoints (Chi tiết)

### 3.1 Query Knowledge Graph

```http
POST /api/v1/graph/query
Authorization: Bearer <token>
Content-Type: application/json
```

**Request Body:**
```json
{
  "query": "What is quantum superposition and how does it relate to entanglement?",
  "top_k_entities": 5,
  "top_k_concepts": 3,
  "document_ids": ["doc_abc123"],
  "include_relations": true
}
```

**Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "entities": [
      {
        "name": "Quantum Superposition",
        "entity_type": "concept",
        "description": "A quantum system can exist in multiple states",
        "similarity": 0.92,
        "source_documents": ["doc_abc123"]
      }
    ],
    "concepts": [
      {
        "name": "Quantum Mechanics",
        "entity_type": "theory",
        "description": "Branch of physics dealing with subatomic particles",
        "connection_count": 4
      }
    ],
    "relations": [
      {
        "source": "Quantum Superposition",
        "target": "Quantum Entanglement",
        "relation_type": "related_to",
        "description": "Both are quantum mechanical phenomena"
      }
    ],
    "assembled_context": "## Relevant Entities\n- **Quantum Superposition**..."
  }
}
```

### 3.2 Get Entity Details

```http
GET /api/v1/graph/entities/{entity_id}
Authorization: Bearer <token>
```

**Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "entity": {
      "id": "ent_xyz789",
      "name": "Quantum Superposition",
      "entity_type": "concept",
      "description": "A fundamental principle of quantum mechanics",
      "confidence": 0.95,
      "source_documents": ["doc_abc123", "doc_def456"]
    },
    "neighbors": [
      {
        "entity_name": "Quantum Entanglement",
        "relation_type": "related_to",
        "relation_description": "Both are quantum phenomena"
      }
    ],
    "metadata": {
      "degree": 5,
      "centrality_score": 0.78
    }
  }
}
```

### 3.3 Extract Subgraph (for Visualization)

```http
POST /api/v1/graph/subgraph
Authorization: Bearer <token>
Content-Type: application/json
```

**Request Body:**
```json
{
  "topic": "Quantum Superposition",
  "max_nodes": 15,
  "max_depth": 2
}
```

**Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "nodes": [
      {
        "id": "quantum_superposition",
        "name": "Quantum Superposition",
        "entity_type": "concept",
        "x": 0,
        "y": 0
      }
    ],
    "edges": [
      {
        "source": "quantum_superposition",
        "target": "quantum_entanglement",
        "relation_type": "related_to"
      }
    ],
    "mermaid_code": "graph TD\n  A[Quantum Superposition] --> B[Quantum Entanglement]"
  }
}
```

### 3.4 Graph Statistics

```http
GET /api/v1/graph/stats
Authorization: Bearer <token>
```

**Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "total_entities": 1234,
    "total_relations": 5678,
    "total_documents": 45,
    "graph_density": 0.023,
    "avg_entities_per_doc": 27.4,
    "most_connected_entities": [
      {
        "name": "Quantum Mechanics",
        "degree": 45
      }
    ],
    "last_updated": "2026-04-05T10:00:00Z"
  }
}
```

---

> [!NOTE]
> Các endpoint này được thiết kế để tối ưu hóa việc chia sẻ ngữ cảnh thông qua MCP, giảm thiểu lượng dữ liệu cần truyền tải giữa các lần gọi AI.
> **LightRAG endpoints** cho phép truy xuất ngữ cảnh giàu ngữ nghĩa hơn traditional RAG.

---

## 4. Dashboard & Settings Endpoints (MVP)

### 4.1 Get Dashboard Data

```http
GET /api/v1/dashboard
```

**Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "stats": {
      "total_documents": 12,
      "total_notes": 23,
      "total_flashcards": 150,
      "due_flashcards_count": 5,
      "total_quiz_avg": 85.0,
      "streak_days": 7
    },
    "recent_documents": [
      {
        "id": "doc_abc123",
        "title": "Neural Networks.pdf",
        "status": "completed",
        "last_activity": "2026-04-10T08:00:00Z"
      }
    ],
    "recent_sessions": [
      {
        "id": "sess_xyz789",
        "type": "chat",
        "last_activity": "2026-04-10T09:30:00Z"
      }
    ],
    "graph_preview": {
      "total_entities": 450,
      "total_relations": 890,
      "top_entities": [
        {"name": "Backpropagation", "degree": 12},
        {"name": "Gradient Descent", "degree": 8}
      ]
    }
  }
}
```

### 4.2 Update Model Settings (Local/Cloud Switch)

```http
POST /api/v1/settings/model
Content-Type: application/json
```

**Request Body:**
```json
{
  "mode": "local",
  "model": "llama3",
  "embedding_provider": "ollama"
}
```

**Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "mode": "local",
    "model": "llama3",
    "embedding_provider": "ollama",
    "ollama_status": "connected",
    "available_models": ["llama3", "mistral", "qwen2.5"]
  }
}
```

**Error Response (400 Bad Request) — Ollama offline:**
```json
{
  "success": false,
  "error": {
    "code": "LLM_UNAVAILABLE",
    "message": "Ollama không phản hồi. Cài đặt: ollama.ai + ollama pull llama3"
  }
}
```
