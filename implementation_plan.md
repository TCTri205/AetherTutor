# Phase 5: Frontend React UI – Implementation Plan

> **Scope:** Week 8–9 | Phase 5 của MVP AetherTutor
> **Người thực hiện:** AetherTutor Team
> **Ngày lập:** April 7, 2026
> **Status:** Draft – Chờ duyệt

---

## Tổng quan

Phase 5 xây dựng toàn bộ giao diện người dùng (React + TypeScript) cho AetherTutor MVP. Sau khi backend (Phase 1–4) đã hoàn chỉnh với đầy đủ API endpoints, bước này kết nối UI đến backend để tạo ra luồng học tập:

```
Upload PDF → LightRAG Processing → Chat (Socratic/Feynman) ↔ Knowledge Graph Viewer
```

Theo `UI_UX_Design_Spec.md §8.4`, tech stack được chọn là:
- **React 18 + TypeScript + Vite**
- **Vanilla CSS** (MVP) — *không dùng Tailwind theo Technical_Spec.md §1 và quy tắc user-global*
- **React Flow** — Graph visualization
- **Zustand** — State management nhẹ
- **Axios** — HTTP client cho REST APIs
- **fetch + ReadableStream** — Xử lý SSE streaming (thay cho EventSource do cần POST body)
- **Framer Motion** — Animations / micro-interactions (P2)
- **Lucide React** — Icons

---

## API Contract đã xác nhận từ Backend (Phase 4)

| Endpoint | Method | Mô tả |
|---|---|---|
| `GET /api/v1/documents/` | GET | Lấy danh sách tài liệu (hỗ trợ `skip`, `limit`) |
| `POST /api/v1/documents/upload` | POST | Upload PDF (trả 202 + `document_id`) |
| `GET /api/v1/documents/{document_id}` | GET | Lấy trạng thái cụ thể của tài liệu |
| `DELETE /api/v1/documents/{document_id}` | DELETE | Xóa tài liệu |
| `GET /api/v1/graph/{document_id}/view` | GET | Lấy nodes & edges của graph |
| `GET /api/v1/graph/{document_id}/stats` | GET | Thống kê graph |
| `POST /api/v1/chat/conversations/{document_id}` | POST | Tạo conversation mới |
| `GET /api/v1/chat/conversations/{document_id}` | GET | Lấy danh sách conversations |
| `POST /api/v1/chat/stream` | POST (SSE) | Chat streaming — body: `{document_id, message, conversation_id?, mode}` |
| `GET /api/v1/chat/history/{conversation_id}` | GET | Lấy lịch sử chat |
| `DELETE /api/v1/chat/conversations/{conversation_id}` | DELETE | Xóa conversation |
| `GET /health` | GET | Health check |

**SSE Stream format** (thực tế từ `chat_service.py`):
```
event: meta
data: {"message_id": "...", "conversation_id": "..."}

event: chunk
data: {"delta": "..."}

event: done
data: {"content_full": "...", "context_used": {...}}

event: error
data: {"detail": "...", "code": "STREAM_INTERRUPTED"}
```

---

## Cấu trúc thư mục Frontend

```
frontend/
├── index.html
├── package.json
├── vite.config.ts              # Proxy /api → localhost:8000
├── tsconfig.json
├── src/
│   ├── main.tsx                 # React entry point
│   ├── App.tsx                  # Router + Layout wrapper
│   ├── index.css                # Design system tokens + global styles
│   │
│   ├── types/                   # TypeScript types (shared)
│   │   ├── document.ts
│   │   ├── chat.ts
│   │   └── graph.ts
│   │
│   ├── api/                     # API client layer
│   │   ├── client.ts            # Axios instance + interceptors
│   │   ├── documents.ts         # Document API calls
│   │   ├── chat.ts              # Chat API calls
│   │   └── graph.ts             # Graph API calls
│   │
│   ├── store/                   # Zustand global state
│   │   ├── documentStore.ts
│   │   ├── chatStore.ts
│   │   └── uiStore.ts           # Theme, sidebar, notifications
│   │
│   ├── hooks/                   # Custom React hooks
│   │   ├── useDocuments.ts
│   │   ├── useChat.ts           # SSE streaming hook
│   │   ├── useGraph.ts
│   │   └── usePolling.ts        # Poll document status
│   │
│   ├── components/              # UI components
│   │   ├── layout/
│   │   │   ├── AppLayout.tsx    # TopNav + Sidebar + Content
│   │   │   ├── TopNav.tsx
│   │   │   ├── Sidebar.tsx
│   │   │   └── StatusBar.tsx
│   │   │
│   │   ├── ui/                  # Base design system components
│   │   │   ├── Button.tsx
│   │   │   ├── Badge.tsx
│   │   │   ├── Card.tsx
│   │   │   ├── Modal.tsx
│   │   │   ├── Toast.tsx        # Toast notifications
│   │   │   ├── Spinner.tsx
│   │   │   ├── ProgressBar.tsx
│   │   │   ├── Skeleton.tsx     # Skeleton loading
│   │   │   └── Tooltip.tsx
│   │   │
│   │   ├── document/
│   │   │   ├── DocumentCard.tsx
│   │   │   ├── DocumentList.tsx
│   │   │   ├── UploadDropzone.tsx
│   │   │   ├── UploadModal.tsx
│   │   │   └── ProcessingStatus.tsx
│   │   │
│   │   ├── chat/
│   │   │   ├── ChatInterface.tsx    # Container chính
│   │   │   ├── MessageList.tsx
│   │   │   ├── MessageBubble.tsx    # User / AI bubble
│   │   │   ├── ContextChips.tsx     # Related entities
│   │   │   ├── StreamingCursor.tsx  # Blinking cursor khi AI đang gõ
│   │   │   ├── ChatInput.tsx        # Multi-line textarea + send
│   │   │   ├── ModeIndicator.tsx    # Socratic/Feynman mode banner
│   │   │   └── ConversationList.tsx # Sidebar list conversations
│   │   │
│   │   └── graph/
│   │       ├── GraphViewer.tsx      # React Flow container
│   │       ├── GraphNode.tsx        # Custom node renderer
│   │       ├── GraphEdge.tsx        # Custom edge renderer
│   │       ├── GraphSidebar.tsx     # Entity details + stats
│   │       └── GraphControls.tsx    # Fit, zoom, layout, search
│   │
│   └── pages/                   # Route-level pages
│       ├── DashboardPage.tsx
│       ├── DocumentsPage.tsx
│       ├── ChatPage.tsx
│       └── GraphPage.tsx
│
└── public/
    └── favicon.ico
```

---

## Kế hoạch triển khai chi tiết (9 Sprints / 2 Tuần)

### Sprint 0: Backend Readiness (Day 1)

> [!IMPORTANT]
> **Dựa trên kiểm tra thực tế code backend** — CORS đã có, `/health` đã có, `/api/v1/chat/stream` đã tồn tại.
> Sprint 0 tập trung vào các **gap thực sự** giữa code hiện tại và yêu cầu Frontend MVP.

#### Tasks

- [ ] **S0.1** Thêm `ProcessingStep` Enum vào `app/models/document.py`:
  ```python
  class ProcessingStep(str, enum.Enum):
      INITIAL = "INITIAL"                  # Mặc định khi PENDING
      EXTRACTING = "EXTRACTING"            # Đang đọc PDF
      CHUNKING = "CHUNKING"                # Chia nhỏ văn bản
      EXTRACTING_ENTITIES = "EXTRACTING_ENTITIES"  # LLM trích xuất tri thức
      BUILDING_GRAPH = "BUILDING_GRAPH"    # Xây dựng quan hệ
      EMBEDDING = "EMBEDDING"              # Lưu vào Vector DB
      COMPLETED = "COMPLETED"              # Hoàn thành
  ```
  - Thêm column `processing_step` vào model `Document` (default = `ProcessingStep.INITIAL`)
  - **Cập nhật `app/core/pipeline.py`** — hàm `ingest_text()`: thêm `update_processing_step()` calls tại từng giai đoạn:
    ```python
    # Trước khi chunk
    await self.doc_repo.update_processing_step(doc_id, ProcessingStep.CHUNKING)
    # Trước khi extract entities
    await self.doc_repo.update_processing_step(doc_id, ProcessingStep.EXTRACTING_ENTITIES)
    # Trước khi build graph
    await self.doc_repo.update_processing_step(doc_id, ProcessingStep.BUILDING_GRAPH)
    # Trước khi lưu ChromaDB
    await self.doc_repo.update_processing_step(doc_id, ProcessingStep.EMBEDDING)
    # Hoàn thành
    await self.doc_repo.update_processing_step(doc_id, ProcessingStep.COMPLETED)
    ```
  - **Cập nhật `app/worker/tasks.py`** — hàm `process_document_task()`: thêm step update trước khi gọi pipeline:
    ```python
    await doc_repo.update_processing_step(doc_id, ProcessingStep.EXTRACTING)
    await pipeline.ingest_text(doc_id, text)  # pipeline sẽ tự update các step tiếp theo
    ```
  - **Thêm method `update_processing_step()`** vào `DocumentRepository`

- [ ] **S0.2** Tạo Alembic Migration cho ProcessingStep:
  ```bash
  alembic revision --autogenerate -m "add processing_step enum to documents"
  alembic upgrade head
  ```
  - Migration thêm enum type `processing_step` vào PostgreSQL
  - Migration thêm column `processing_step` vào bảng `documents`

- [ ] **S0.3** Cập nhật `DocumentDetail` Schema (`app/schemas/lightrag.py`):
  ```python
  class DocumentDetail(BaseModel):
      # ... existing fields ...
      processing_step: Optional[str] = None  # NEW
      entity_count: int = 0                   # NEW (alias total_entities)
      relation_count: int = 0                 # NEW (alias total_relationships)
      page_count: Optional[int] = None        # NEW
      file_size: Optional[int] = None         # NEW (bytes)
  ```
  - **Cập nhật `app/api/documents.py`** — endpoint `list_documents` và `get_document_status`:
    - Query graph stats (`graph_repo.count_by_document_id`) để lấy entity_count, relation_count
    - Map các field mới vào response

- [ ] **S0.4** Sửa Upload Endpoint (`app/api/documents.py`) — Duplicate Hash Handling:
  - **Vấn đề hiện tại:** Endpoint có `status_code=HTTPStatus.ACCEPTED` (hard-coded 202) trong decorator → dù service trả về existing doc, FastAPI vẫn ghi đè status thành 202.
  - **Giải pháp:** Không dùng `status_code` parameter trong decorator — trả về `JSONResponse` với status tùy ý trong body.
  - **Cập nhật `app/services/document_service.py`** — `upload_document()`:
    - Trả về tuple `(Document, bool)` với bool = `True` nếu là existing doc (trùng hash)
    ```python
    async def upload_document(self, file: UploadFile) -> tuple[Document, bool]:
        # ... validation ...
        existing_doc = await self.repo.get_by_hash(content_hash)
        if existing_doc:
            return existing_doc, True  # is_duplicate = True
        # ... create new doc ...
        return doc, False  # is_duplicate = False
    ```
  - **Cập nhật `app/api/documents.py`** — `upload_document()`:
    ```python
    from fastapi.responses import JSONResponse

    @router.post("/upload")  # BỎ CẢ response_model VÀ status_code — trả JSONResponse trực tiếp
    async def upload_document(
        file: UploadFile = File(...),
        service: DocumentService = Depends(get_doc_service)
    ):
        doc, is_duplicate = await service.upload_document(file)

        if is_duplicate:
            # File đã tồn tại — trả về 200 OK, frontend KHÔNG cần polling
            return JSONResponse(
                status_code=200,
                content={
                    "document_id": str(doc.id),
                    "filename": doc.filename,
                    "status": doc.status,
                    "message": "Tài liệu này đã tồn tại trong hệ thống."
                }
            )
        else:
            # File mới — trả về 202 Accepted, frontend CẦN polling
            return JSONResponse(
                status_code=202,
                content={
                    "document_id": str(doc.id),
                    "filename": doc.filename,
                    "status": doc.status,
                    "message": "Yêu cầu đã được tiếp nhận và đang được xử lý trong hàng đợi."
                }
            )
    ```
  - **Cập nhật `app/schemas/lightrag.py`**: Tạo `DocumentUploadResponse` mới (optional — dùng dict thay thế cũng được)
  - Frontend dựa vào status code để biết có cần polling hay không (200 = skip polling, navigate ngay; 202 = start polling)

- [ ] **S0.5** Thêm `found_entities` vào SSE `done` Event — CRITICAL (cần sửa cả `retriever.py` + `chat_service.py`):
  - **Vấn đề hiện tại:** `retriever.retrieve()` trả về `context` list với `type: "chunk"` và `type: "relation"` — **KHÔNG có `type: "entity"`**. Entity names chỉ nằm trong biến nội bộ `found_entity_names` (từ ChromaDB query) nhưng không được đưa vào context. Do đó, logic parse `found_entities` từ context sẽ **luôn trả về rỗng**.
  - **Giải pháp:** Sửa `retriever.retrieve()` trả về tuple `(context, entity_names)` thay vì chỉ `context`.
  - **Bước 1 — Cập nhật `app/core/retriever.py`** — hàm `retrieve()`:
    ```python
    async def retrieve(self, query: str, document_id: str, top_k: int = 5) -> tuple[List[Dict[str, Any]], List[str]]:
        """
        Dual-level retrieval from ChromaDB and SQL Graph.
        Returns: (context list, found entity names)
        """
        context = []
        doc_uuid = uuid.UUID(document_id)

        # 1. Vector Search: Chunks
        chunks_res = chroma_client.chunks_collection.query(
            query_texts=[query],
            n_results=top_k,
            where={"document_id": document_id}
        )
        for i in range(len(chunks_res['ids'][0])):
            context.append({
                "type": "chunk",
                "content": chunks_res['documents'][0][i],
                "metadata": chunks_res['metadatas'][0][i]
            })

        # 2. Vector Search: Entities
        entities_res = chroma_client.entities_collection.query(
            query_texts=[query],
            n_results=3,
            where={"document_id": document_id}
        )
        found_entity_names = [m['entity_name'] for m in entities_res['metadatas'][0]]

        # 3. Graph Traversal: Neighbors
        if found_entity_names:
            relations = await self.graph_repo.get_entity_neighbors(doc_uuid, found_entity_names)
            for rel in relations:
                context.append({
                    "type": "relation",
                    "content": f"{rel.source_entity} --({rel.relation_type})--> {rel.target_entity}: {rel.description}",
                    "metadata": {"source": rel.source_entity, "target": rel.target_entity}
                })

        return context, found_entity_names  # <-- TRẢ VỀ TUPLE
    ```
  - **Bước 2 — Cập nhật `app/services/chat_service.py`** — hàm `chat_stream()`:
    ```python
    # 3. Retrieve Context (Hybrid: Top-k chunks/graph)
    context, found_entities = await self.retriever.retrieve(user_query, str(document_id))
    # found_entities = list of entity names từ ChromaDB query
    context_str = "\n".join([f"[{c['type']}] {c['content']}" for c in context])
    ```
  - Gửi trong `done` event (với `default=str` để handle UUID/datetime):
    ```python
    yield f"event: done\ndata: {json.dumps({
        'content_full': full_content,
        'context_used': assistant_msg.context_used,
        'found_entities': found_entities  # NEW: list of entity names
    }, default=str)}\n\n"
    ```
  - **Cập nhật các chỗ gọi `retriever.retrieve()` khác:**
    - `app/api/graph.py` — `query_graph()`: unpack tuple
    - `app/core/retriever.py` — `generate()`: nhận context trực tiếp (không thay đổi)
    - `app/api/chat.py` — `socratic_chat_legacy()`: unpack tuple, bỏ `entity_names`

- [ ] **S0.6** Cập nhật `/health` Endpoint (`app/main.py`) — LLM Metadata:
  - **Vấn đề hiện tại:** Chỉ check postgres/redis/chromadb, không có thông tin LLM.
  - **Cập nhật:**
    ```python
    from .config import settings

    # Xác định provider
    if settings.OPENAI_API_KEY:
        provider = "openai"
        mode = "cloud"
    else:
        provider = "ollama"
        mode = "local"

    # Check LLM connectivity (ping Ollama hoặc OpenAI)
    llm_healthy = await llm_service.health_check()  # Cần thêm method này

    return {
        "status": overall_status,
        "services": { "postgres": ..., "redis": ..., "chromadb": ... },
        "llm": {
            "model": settings.DEFAULT_LLM_MODEL,
            "embedding_model": settings.DEFAULT_EMBEDDING_MODEL,
            "provider": provider,
            "mode": mode,  # "local" hoặc "cloud"
            "healthy": llm_healthy
        }
    }
    ```
  - **Thêm `health_check()` method** vào `app/services/llm_service.py`:
    - Ollama: GET `{OLLAMA_BASE_URL}/api/tags` hoặc đơn giản hơn là thử gửi request nhỏ
    - OpenAI: GET `https://api.openai.com/v1/models` với API key
  - Frontend dùng thông tin này để hiển thị LLM Mode Badge (🔒 Local / 🌐 Cloud)

- [ ] **S0.7** Thêm CORS Middleware (`app/main.py`) — CRITICAL:
  - **Vấn đề hiện tại:** Backend **KHÔNG CÓ** CORS middleware — frontend `localhost:5173` sẽ bị trình duyệt chặn request sang backend `localhost:8000`.
  - **Cập nhật:**
    ```python
    from fastapi.middleware.cors import CORSMiddleware

    # Sau khi tạo app:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:5173",   # Vite dev server
            "http://localhost:3000",   # Alternative dev port
            "http://127.0.0.1:5173",
            "http://127.0.0.1:3000",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    ```
  - **Production note:** Khi deploy, thay origins bằng domain thật của frontend
  - Frontend không cần cấu hình gì thêm — Vite proxy sẽ hoạt động bình thường

---

### Sprint 1: Project Bootstrap & Design System (Day 1–2)

**Mục tiêu:** Khởi tạo project, thiết lập design system, routing.

#### Tasks

- [ ] **S1.1** Scaffold Vite + React + TypeScript project
  ```bash
  cd d:\Projects_IT\AetherTutor
  npx -y create-vite@latest frontend -- --template react-ts
  cd frontend && npm install
  ```

  ```bash
  # Core & UI
  npm install axios zustand reactflow framer-motion lucide-react react-router-dom
  # Markdown & Graph Layout
  npm install react-markdown remark-gfm @dagrejs/dagre
  # Optimization & Error Handling
  npm install @tanstack/react-virtual react-error-boundary
  # Dev Tools & Mocking
  npm install -D vitest @testing-library/react msw
  # Dev Types
  npm install -D @types/react @types/react-dom @types/dagre
  ```

- [ ] **S1.2b** Cấu hình `tsconfig.json` (P1)
  - Bật `strict: true`
  - `exactOptionalPropertyTypes: true`
  - `noUnusedLocals: true`

- [ ] **S1.2c** Setup MSW (P1): Cấu hình Mock Service Worker để phát triển Frontend độc lập.

- [ ] **S1.2d** `.env.example` (P2): Tạo file mẫu với `VITE_API_BASE_URL=/api/v1` và `VITE_APP_NAME=AetherTutor`.

- [ ] **S1.3** Cấu hình `vite.config.ts` với proxy
  ```typescript
  // Proxy /api/* → http://localhost:8000 (dev mode)
  server: {
    proxy: {
      '/api': 'http://localhost:8000',
      '/health': 'http://localhost:8000'
    }
  }
  ```

- [ ] **S1.4** Xây dựng `src/index.css` — Design System Tokens
  - Colors (primary indigo, accent amber, semantic)
  - Typography (Inter + Plus Jakarta Sans từ Google Fonts)  
  - Spacing scale (4px base)
  - Border radius, shadows, transitions
  - Skeleton shimmer animation keyframe
  - Dark mode selectors (`.dark` class — nice-to-have MVP)

- [ ] **S1.5** Xây dựng `src/types/` — TypeScript interfaces
  - `Document`, `DocumentStatus` enum, `DocumentDetail`
  - `Conversation`, `Message`, `MessageRole` enum
  - `GraphNode`, `GraphEdge`, `GraphStats`
  - `ChatStreamRequest`, `SSEEvent` types

- [ ] **S1.6** Khởi tạo React Router v6 trong `App.tsx`
  ```tsx
  // Routes: / → Dashboard, /documents → Docs, /chat/:docId/:convId? → Chat,
  // /graph/:docId → Graph
  ```

---

### Sprint 2: API Client & State Management (Day 1–2)

**Mục tiêu:** Lớp data hoàn chỉnh — từ API calls đến global state.

#### Tasks

- [ ] **S2.1** `src/api/client.ts` — Axios instance
  - baseURL = `/api/v1`
  - **Response Interceptor** (quan trọng — backend KHÔNG có global error handler, có thể trả HTML thay vì JSON):
    ```typescript
    api.interceptors.response.use(
      (response) => {
        // Check content-type — nếu không phải JSON → xử lý đặc biệt
        const ct = response.headers['content-type'] || '';
        if (!ct.includes('application/json') && !ct.includes('text/event-stream')) {
          // Backend trả HTML error page (500) hoặc file khác
          console.error('Non-JSON response detected:', ct);
          return Promise.reject(new ApiError(502, 'Lỗi máy chủ nội bộ — vui lòng thử lại sau'));
        }
        return response;
      },
      (error) => {
        if (error.response) {
          const ct = error.response.headers['content-type'] || '';
          // Nếu là HTML error page → chuyển thành JSON error
          if (ct.includes('text/html')) {
            return Promise.reject(new ApiError(
              error.response.status || 502,
              'Lỗi máy chủ nội bộ — vui lòng thử lại sau'
            ));
          }
          // Lấy message từ response body nếu có
          const detail = error.response.data?.detail || error.response.data?.message || 'Lỗi không xác định';
          return Promise.reject(new ApiError(error.response.status, detail));
        }
        if (error.request) {
          // Network error — không nhận được response
          return Promise.reject(new ApiError(0, 'Mất kết nối mạng — kiểm tra lại và thử lại'));
        }
        return Promise.reject(error);
      }
    );
    ```
  - **Custom `ApiError` class**:
    ```typescript
    export class ApiError extends Error {
      constructor(public status: number, message: string) {
        super(message);
        this.name = 'ApiError';
      }
    }
    ```
  - Retry 1 lần khi 502/503 (chỉ áp dụng cho GET requests, không retry POST multipart upload)
  - Response normalizer: transform snake_case response sang camelCase (optional, P2)

- [ ] **S2.2** `src/api/documents.ts`
  ```typescript
  getDocuments(): Promise<DocumentDetail[]>
  uploadDocument(file: File): Promise<DocumentUploadResponse>  // multipart
  getDocument(id: string): Promise<DocumentDetail>
  deleteDocument(id: string): Promise<void>
  ```

- [ ] **S2.3** `src/api/chat.ts`
  ```typescript
  createConversation(docId: string, title?: string): Promise<Conversation>
  listConversations(docId: string): Promise<Conversation[]>
  getChatHistory(convId: string): Promise<ConversationDetail>
  deleteConversation(convId: string): Promise<void>
  // SSE requests được xử lý bởi custom hook, không phải Axios
  ```

- [ ] **S2.4** `src/api/graph.ts`
  ```typescript
  getGraphView(docId: string): Promise<{nodes: GraphNode[], edges: GraphEdge[]}>
  getGraphStats(docId: string): Promise<GraphStats>
  ```

- [ ] **S2.5** `src/store/documentStore.ts` — Zustand
  ```typescript
  // State: documents[], selectedDocId, loading, error
  // Actions: fetchDocuments, uploadDocument, deleteDocument, setSelected
  ```

- [ ] **S2.6** `src/store/chatStore.ts` — Zustand
  ```typescript
  // State: conversations[], activeConvId, messages[], isStreaming, streamBuffer
  // Actions: createConversation, setActiveConv, appendMessage, updateLastMessage
  ```

- [ ] **S2.7** `src/store/uiStore.ts` — Zustand
  ```typescript
  // State: sidebarCollapsed, toasts[], activeRoute, isDark
  // Actions: addToast, removeToast, toggleSidebar
  ```

- [ ] **S2.8** `src/hooks/useChat.ts` — Robust SSE Hook (P0)
  - **Buffered Parser**: Sử dụng buffer string để tích lũy dữ liệu cho đến khi gặp `\n\n`.
  - Hỗ trợ `AbortController` để ngắt stream.
  - **SSE Retry Logic (P0)**:
    - Retry chỉ áp dụng khi **POST request thất bại trước khi nhận `meta` event** (network error, 502/503).
    - Retry tối đa 3 lần với exponential backoff (1s → 2s → 4s).
    - Sau khi nhận `meta` event → nếu stream disconnect giữa chừng → **KHÔNG retry tự động** mà hiển thị error state (vì message đã được commit ở trạng thái PENDING/FAILED). User phải chủ động nhấn Retry.
    - Callback `onRetry?(attempt: number)` để UI hiển thị "Đang thử lại... (lần {attempt})".

- [ ] **S2.9** `src/hooks/usePolling.ts` — Document Status Polling (P0)
  - Poll GET `/api/v1/documents/{document_id}` mỗi 3 giây.
  - **Document Deletion Guard**: Nếu poll trả về 404 → document đã bị xóa → redirect về `/documents` + toast "Tài liệu này đã bị xóa."
  - **Auto-stop polling**: khi status = COMPLETED hoặc FAILED → dừng polling ngay.
  - **Conversation Title Sync**: Sau khi poll thấy COMPLETED, tiếp tục poll thêm 5s (max 5 lần) để đợi backend `generate_conversation_title` hoàn thành → cập nhật conversation list nếu title thay đổi.

- [ ] **S2.10** `src/components/guards/RouteGuard.tsx` (P1)
  - Kiểm tra trạng thái document trước khi cho phép vào `/chat`.

- [ ] **S2.11** `src/api/interceptors.ts` (P1): Xử lý case file trùng hash (Backend trả 200).

---

### Sprint 3: Base UI Components (Day 2)

**Mục tiêu:** Xây dựng design system components tái sử dụng.

#### Tasks

- [ ] **S3.1** `Button.tsx` — Primary, Secondary, Ghost variants + loading state

- [ ] **S3.2** `Badge.tsx` — Success (green), Warning (amber), Error (red), Info (blue) + animated pulse cho "Processing"

- [ ] **S3.3** `Card.tsx` — base card với hover lift effect (translateY -4px + shadow)

- [ ] **S3.4** `Modal.tsx` — Portal-based modal, backdrop click to close, ESC key, `framer-motion` scale animation

- [ ] **S3.5** `Toast.tsx` + Toast container
  - Slide in from bottom-right
  - Auto-dismiss sau 4s
  - Types: success, error, warning, info
  - Connected vào `uiStore.toasts`

- [ ] **S3.6** `Spinner.tsx` — CSS spin animation

- [ ] **S3.7** `ProgressBar.tsx` — Linear animated progress

- [ ] **S3.8** `Skeleton.tsx` — Shimmer skeleton cho document list, chat history

- [ ] **S3.9** `Tooltip.tsx` — Hover tooltip (dùng cho disabled buttons "Coming soon")

---

### Sprint 4: App Layout (Day 2–3)

**Mục tiêu:** Shell UI hoàn chỉnh với TopNav + Sidebar + Content area.

#### Tasks

- [ ] **S4.1** `AppLayout.tsx` — Grid layout: sidebar (260px fixed) + main content area

- [ ] **S4.2** `TopNav.tsx`
  - Logo AetherTutor (text + icon)
  - **LLM Mode Badge**: `🔒 Local (Qwen)` hoặc `🌐 Cloud` — connect `/health` để detect backend
  - Hamburger (mobile sidebar toggle)

- [ ] **S4.3** `Sidebar.tsx`
  - Nav items: Home 🏠, Documents 📚, Chat 💬, Graph 🕸️
  - Active state: primary color bg + left border 3px
  - Hover: gray tint 150ms transition
  - Collapsible → 72px icon-only mode
  - Sub-item: khi chọn document, hiện "Chat" và "Graph" links kèm doc name

- [ ] **S4.4** `StatusBar.tsx` (optional, nice-to-have)
  - Processing queue count
  - Backend health indicator

---

### Sprint 5: Document Pages (Day 3)

**Mục tiêu:** Màn hình Documents hoàn chỉnh với upload, list, và status tracking.

#### Tasks

- [ ] **S5.1** `UploadDropzone.tsx`
  - Drag & drop + click to browse
  - File type validation (PDF only, max 50MB)
  - File size display
  - Visual feedback khi dragging (dashed border glow)

- [ ] **S5.2** `UploadModal.tsx`
  - Single file upload focus (theo Backend MVP).
  - Hiển thị tên file, dung lượng.
  - Sau khi upload (202), chuyển ngay về trạng thái `PROCESSING` với granular steps.

- [ ] **S5.3** `ProcessingStatus.tsx`
  - Steps: Extract text → Chunk → Extract entities → Build graph → Embed
  - Animated step indicators (✅ done, ⏳ in-progress, ○ waiting)
  - Polling integration via `usePolling` hook

- [ ] **S5.4** `DocumentCard.tsx`
  - Filename, status badge, entity/relation count (từ graph stats)
  - Upload time, file size, pages (nếu có)
  - Action buttons: 💬 Chat, 🕸️ Graph, 🗑️ Delete
  - Hover lift effect

- [ ] **S5.5** `DocumentList.tsx`
  - Filter tabs: All | Processing | Completed | Failed
  - Sort by: Recent | Name
  - Empty state component (§4.0.2 từ UI_UX spec)
  - Skeleton loading placeholders
  - **Pagination**: "Load more" button ở cuối danh sách (simple approach cho MVP — mỗi lần load thêm 10 docs)
  - Backend hỗ trợ `skip` + `limit` → frontend tracking `currentSkip` state, increment sau mỗi lần "Load more"

- [ ] **S5.6** `DocumentsPage.tsx` — route `/documents`
  - Header + Upload button
  - Filter/sort controls
  - DocumentList component
  - Toast on upload success/failure

- [ ] **S5.7** `DashboardPage.tsx` — route `/`
  - Empty state khi chưa có document (§4.0.1)
  - Quick Actions panel (Upload PDF, Start Chat, View Graph)
  - Recent Documents list (3-5 items)
  - Backend health indicator

---

### Sprint 6: Chat Interface (Day 4–5)

**Mục tiêu:** Màn hình Chat hoàn chỉnh với SSE streaming.

> [!IMPORTANT]
> Đây là P0 component — core value proposition của AetherTutor. Cần thực hiện kỹ lưỡng nhất.

#### Tasks

- [ ] **S6.1** `ModeIndicator.tsx`
  - Banner hiển thị: "🎭 Socratic Tutor • Feynman Technique"
  - Graph stats: "Graph-aware: X entities, Y relations loaded"
  - Combo selector dropdown (A/B/C/D — theo Methodology.md)

- [ ] **S6.2** `StreamingCursor.tsx`
  - CSS blinking cursor animation
  - Chỉ hiển thị khi `isStreaming === true`

- [ ] **S6.3** `ContextChips.tsx`
  - Pill badges hiển thị names của các entities được tìm thấy trong context (từ SSE `done` event's `found_entities`).
  - Xuất hiện dưới mỗi AI message.
  - Click → navigate sang Graph Viewer và highlight node tương ứng.

- [ ] **S6.4** `MessageBubble.tsx`
  - User bubble: right-aligned, primary color bg
  - AI bubble: left-aligned, light bg + AI avatar icon
  - Timestamp display
  - Markdown rendering dùng `react-markdown` + `remark-gfm`
  - Hỗ trợ code blocks, tables, lists trong AI responses
  - Streaming state: hiển thị `StreamingCursor` ở cuối

- [ ] **S6.5** `MessageList.tsx`
  - Virtualized list dùng `@tanstack/react-virtual`
  - Tối ưu hiệu năng khi cuộc hội thoại kéo dài (>100 messages)
  - Auto-scroll to bottom khi có message mới
  - Loading skeleton cho initial history fetch
  - "AI đang suy nghĩ..." indicator

- [ ] **S6.6** `ChatInput.tsx`
  - Multi-line textarea, auto-resize (min 48px, max 200px)
  - Placeholder suggestions: "Giải thích backpropagation..."
  - Send on Enter (Shift+Enter = newline)
  - Disabled khi `isStreaming === true`
  - Character count (optional)

- [ ] **S6.7** `ConversationList.tsx`
  - Sidebar list các conversations của document hiện tại
  - New conversation button
  - Delete conversation
  - Active state highlight
  - **Data source**: `GET /api/v1/chat/conversations/{document_id}` trả về `ConversationRead[]` — chỉ có `id, document_id, title, created_at, last_message_at` — **KHÔNG có messages**.
  - **Không cần gọi thêm API** để hiển thị list — chỉ cần 1 call duy nhất.
  - **Fallback title handling**: Khi `title` null/trống → hiển thị "Hội thoại #1", "#2"... (dựa trên created_at order)
    - Backend default title = `"Cuộc hội thoại mới"` → nếu title này quá generic, frontend vẫn hiển thị "Hội thoại #N" để dễ phân biệt
  - **Title auto-update**: Backend generate title bất đồng bộ (background task, ~5-10s). Frontend:
    - Poll conversation list mỗi 3s, tối đa 5 lần sau khi tạo conversation mới
    - Nếu title thay đổi từ `"Cuộc hội thoại mới"` → value khác → cập nhật UI
    - Nếu sau 15s title vẫn `"Cuộc hội thoại mới"` → hiển thị fallback "Hội thoại #N"

- [ ] **S6.8** `ChatInterface.tsx` — Container chính
  - Ghép: ConversationList sidebar + ModeIndicator + MessageList + ChatInput
  - Error state UI (§4.0.4): "⚠️ AI không phản hồi" + Retry
  - `useChat` hook integration:
    ```
    1. User gửi message
    2. Append user message lên UI ngay (optimistic)
    3. POST /api/v1/chat/stream với SSE
    4. Accumulate delta events → render streaming
    5. On 'done': finalize message, clear streaming cursor
    6. On 'error': show toast + error bubble
    ```

- [ ] **S6.9** `ChatPage.tsx` — route `/chat/:docId/:convId?`
  - Load document info từ `documentStore`
  - Load/create conversation từ `chatStore`
  - Render ChatInterface với correct props
  - Guard: redirect nếu document không tồn tại hoặc status != COMPLETED
  - **Document Deletion Guard**: Nếu poll phát hiện 404 → redirect về `/documents` + toast
  - **Orphaned Conversation Guard**: Nếu conversation_id không thuộc document_id → redirect và tạo conversation mới

- [ ] **S6.10** MVP Scope Constraint — Feynman Test Only (theo §8.1 UI_UX spec)
  - Trong Mode Indicator, chỉ kích hoạt **Feynman Test** mode
  - Các nút **Diagram** và **Quiz** ở trạng thái **disabled**:
    - Greyed out + cursor-not-allowed
    - Tooltip: "Coming soon"
  - Khi user click vào disabled button → toast info: "Tính năng sẽ ra mắt trong bản cập nhật tới"

---

### Sprint 7: Knowledge Graph Viewer (Day 5–6)

**Mục tiêu:** Graph visualization với React Flow — **MVP basic scope** (theo §8.1 UI_UX spec).

> [!NOTE]
> MVP chỉ yêu cầu basic graph viewer + search entity. Các tính năng nâng cao (Dagre layout, filter by type, performance test) chuyển **POST-MVP**.

#### Tasks

- [ ] **S7.1** `GraphNode.tsx` — Custom React Flow node
  - Circle shape cho concepts, rounded rect cho terms
  - Color by entity_type (concept=indigo, term=amber, process=green, theory=purple)
  - Label always visible khi zoom > 0.7, else hidden
  - Hover: glow effect + description tooltip

- [ ] **S7.2** `GraphEdge.tsx` — Custom React Flow edge
  - Bezier curve
  - Label = relation_type (**hidden** trong MVP, chỉ hiện trên hover tooltip)
  - Color: default gray, selected = primary indigo
  - Subtle arrow direction marker

- [ ] **S7.3** Simple Layout cho MVP
  - **KHÔNG dùng Dagre** trong MVP — dùng simple radial layout từ tâm (0,0)
  - Tính toán vị trí: node đầu tiên tại (0,0), các node xung quanh theo vòng tròn bán kính 200px
  - Auto-fit on mount
  - *Post-MVP:* Upgrade lên Dagre hierarchical layout

- [ ] **S7.4** `GraphControls.tsx` — MVP basic
  - Fit View button
  - Zoom In / Zoom Out
  - **Search input**: filter nodes by name (highlight matching, dim others) — **MVP required**
  - ~~Layout toggle~~ — **POST-MVP**
  - ~~Filter by entity_type checkboxes~~ — **POST-MVP**

- [ ] **S7.5** `GraphSidebar.tsx`
  - Hiển thị khi click một node
  - Entity name, type (badge), description
  - Relationships list (neighbors) với relation_type
  - Degree count
  - "💬 Chat về entity này" button → open chat với pre-filled query

- [ ] **S7.6** `GraphViewer.tsx` — Container
  - Fetch `/api/v1/graph/{docId}/view` + `/stats`
  - Transform API response → React Flow nodes/edges format:
    ```typescript
    // nodes: {id, type: 'graphNode', data: {...entity}, position: {x,y}}
    // edges: {id, source, target, type: 'graphEdge', data: {...relation}}
    ```
  - Apply simple radial layout
  - Render ReactFlow với custom node/edge types
  - Loading skeleton
  - Empty state: "Chưa có knowledge graph. Upload và xử lý tài liệu trước."

- [ ] **S7.7** `GraphPage.tsx` — route `/graph/:docId`
  - GraphViewer + GraphSidebar (right panel)
  - Graph stats summary (entity count, relation count)
  - Link back to Chat
  - **Document Deletion Guard**: Nếu poll phát hiện 404 → redirect về `/documents` + toast

---

### Sprint 8: Polish, Empty/Error States & Final Integration (Day 6–7)

**Mục tiêu:** Hoàn thiện UX, xử lý edge cases, kiểm thử end-to-end.

#### Tasks

- [ ] **S8.1** Empty States (theo §4.0.1-4.0.2 trong UI_UX spec)
  - Dashboard empty state: welcome message + upload CTA
  - Documents empty state: illustration + upload button
  - Graph empty state: "Processing chưa xong" indicator
  - Chat empty state: "Bắt đầu cuộc hội thoại" placeholder

- [ ] **S8.1a** Error State: LLM Timeout (theo §4.0.3)
  - Message: "AI đang bận xử lý câu hỏi của bạn — thử lại nhé"
  - Actions: [Retry] [Switch to Local Mode]
  - Trigger: Khi SSE stream timeout hoặc 504 Gateway

- [ ] **S8.1b** Error State: File >50MB (theo §4.0.3)
  - Message: "File quá lớn (giới hạn 50MB). Hãy chọn file nhỏ hơn."
  - Action: [Dismiss] — không có retry
  - Trigger: Upload validation fail (HTTP 413)

- [ ] **S8.1c** Error State: PDF Scan (no text layer) (theo §4.0.3)
  - Message: "PDF này là ảnh scan — hệ thống không đọc được text. Hãy dùng file PDF có text."
  - Action: [Dismiss] — không có retry
  - Trigger: Background worker detect scanned PDF

- [ ] **S8.1d** Error State: Invalid API Key (theo §4.0.3)
  - Message: "API Key không hợp lệ. Vui lòng kiểm tra cài đặt."
  - Action: [Go to Settings]
  - Trigger: LLM provider trả về 401 Unauthorized

- [ ] **S8.1e** Error State: Network Failure (theo §4.0.3)
  - Message: "Mất kết nối mạng — kiểm tra lại và thử lại nhé"
  - Actions: [Retry] [Switch to Local Mode]
  - Trigger: Fetch request fail (network error, offline)

- [ ] **S8.1f** Error State: Chat AI không phản hồi (theo §4.0.4)
  - Message: "⚠️ AI không phản hồi — có thể do API key, mạng, hoặc model đang quá tải"
  - Actions: [Retry] [Check Settings]
  - Trigger: SSE stream không nhận được chunk nào sau 30s

- [ ] **S8.2** Global Error Boundary (P1)
  - Sử dụng `react-error-boundary`.
  - Wrap ở **Route Level** (từng trang) để đảm bảo lỗi ở một trang không làm hỏng toàn bộ app.

- [ ] **S8.3** Micro-animations (P2 - Framer Motion)
  - Page transitions, modal scales, toast slides.

- [ ] **S8.4** Responsive Layout (P1)
  - Mobile/Tablet support.

- [ ] **S8.5** Accessibility & README (P2)
  - ARIA labels, Keyboard navigation.
  - Viết `README.md` hướng dẫn setup, env vars, build.

- [ ] **S8.6** Final UI Polish & Deployment Ready
  - Kiểm tra lại toàn bộ color contrast, spacing.
  - Xử lý các edge cases về overflow text trong chat bubbles.
  - Tối ưu hóa build bundle: `npm run build`.

- [ ] **S8.7** End-to-End Integration Test
  - **Flow 1:** Upload PDF → polling status → "Completed" toast → navigate to Chat
  - **Flow 2:** Chat → SSE streaming → context chips → navigate to Graph
  - **Flow 3:** Graph node click → Chat with pre-filled query
  - **Flow 4:** Error recovery — upload fail, chat fail, network offline

- [ ] **S8.8** Update `frontend/package.json` scripts
  ```json
  {
    "scripts": {
      "dev": "vite",
      "build": "tsc && vite build",
      "preview": "vite preview"
    }
  }
  ```

---

## Các điểm cần đặc biệt chú ý

### ⚡ SSE Streaming Implementation

API `/api/v1/chat/stream` dùng `StreamingResponse` với `text/event-stream`. Frontend **không thể dùng Axios** cho SSE — phải dùng `fetch` với `ReadableStream` hoặc native `EventSource` (EventSource không hỗ trợ POST body).

**Recommended approach:**
```typescript
const response = await fetch('/api/v1/chat/stream', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(request)
});
const reader = response.body!.getReader();
const decoder = new TextDecoder();
// Read chunks, parse SSE lines, dispatch to store
```

**Retry Strategy:**
- **Retry chỉ áp dụng trước khi nhận `meta` event** (network error, 502/503). Retry max 3 lần, exponential backoff.
- **Sau khi nhận `meta` event** → stream disconnect → **KHÔNG retry tự động**. Backend đã commit message ở trạng thái PENDING/FAILED. User nhấn Retry để gửi lại message.
- Timeout: 120s (khớp với backend `asyncio.timeout(120)`). Nếu không nhận chunk nào sau 30s → hiển thị error state S8.1f.

**`found_entities` parsing:**
- Backend gửi `found_entities: string[]` trong `done` event — danh sách entity names từ retrieval context.
- Frontend parse và render thành ContextChips dưới mỗi AI message.

### ⚡ Conversation Title Sync

Backend generate title bất đồng bộ (background task, có thể mất 5-10s). Frontend cần:
1. Khi tạo conversation mới → hiển thị placeholder "Đang đặt tên..."
2. Poll conversation list mỗi 3s, tối đa 5 lần → khi title xuất hiện → cập nhật UI
3. Fallback: Nếu title vẫn null sau 15s → hiển thị "Hội thoại #N"

### ⚡ React Flow Node Layout

React Flow không tự layout nodes. **MVP strategy:** Dùng simple radial layout (node đầu tiên tại tâm, các node xung quanh theo vòng tròn). Post-MVP upgrade lên Dagre hierarchical layout.

### ⚡ Polling vs WebSocket

Backend Phase 4 không có WebSocket support — dùng polling (mỗi 3s) để check document processing status. Đủ cho MVP.

### ⚡ Tech Stack Decision Note

Theo UI_UX_Design_Spec §8.4 đề xuất "Tailwind CSS" và "Socket.io-client", nhưng:
- **§2 của cùng spec** ghi rõ "Vanilla CSS (MVP), Tailwind là post-MVP option" → **Chọn Vanilla CSS**
- Backend dùng SSE `text/event-stream`, không phải Socket.io → **Chọn fetch + ReadableStream**
- Quyết định này nhất quán với Technical_Spec §1 và quy tắc user-global

---

| File | Thay đổi | Lý do |
|---|---|---|
| `app/models/document.py` | Thêm `ProcessingStep` Enum + column | Granular UI progress tracking |
| `alembic/versions/` | Tạo migration mới | Migration cho ProcessingStep enum |
| `app/schemas/lightrag.py` | Bổ sung 5 fields mới vào `DocumentDetail` | Đồng bộ dữ liệu Dashboard/Library |
| `app/api/documents.py` | Trả về HTTP 200 nếu trùng hash; map fields mới | Tránh polling vô ích; hiển thị entity/relation count |
| `app/services/document_service.py` | Trả tuple `(doc, is_duplicate)` | Để endpoint phân biệt 200 vs 202 |
| `app/repositories/document_repo.py` | Thêm `update_processing_step()` | Cập nhật step trong pipeline |
| `app/core/pipeline.py` | Thêm `update_processing_step()` calls | Report progress cho frontend |
| `app/worker/tasks.py` | Thêm step update trước pipeline | Report EXTRACTING step |
| `app/services/chat_service.py` | Thêm `found_entities` trong `done` event | Context Chips UI |
| `app/main.py` | Thêm LLM metadata vào `/health` | LLM Mode Badge |
| `app/services/llm_service.py` | Thêm `health_check()` method | Kiểm tra LLM connectivity |

---

## Deliverables Phase 5

| Deliverable | Tiêu chí "Done" |
|---|---|
| ✅ Dashboard | Hiển thị quick actions + recent documents. Empty state khi chưa có docs. |
| ✅ Document Upload UI | Drag & drop PDF, validation, upload, polling đến COMPLETED/FAILED |
| ✅ Document Library | Danh sách với filter/sort, status badges, action buttons |
| ✅ Chat Interface | SSE streaming hoạt động, Socratic mode, context chips, error recovery |
| ✅ Graph Viewer | React Flow render nodes/edges, simple radial layout, search entity, node click → detail panel |
| ✅ App Layout | TopNav + Sidebar responsive, LLM Mode Badge, navigation giữa pages |
| ✅ Empty States | Dashboard, Library, Chat, Graph đều có empty state properly |
| ✅ Error States | Upload fail, chat fail, network error — đều có UI + recovery action |
| ✅ Animations | Page transitions, modal, toast, card hover, streaming cursor |

---

## Verification Plan

### Automated Tests (Critical)
- [ ] **Unit Test: SSE Parser**: Kiểm tra việc parse các chunks bị cắt rời, gộp nhiều events, và các events lạ.
- [ ] **Unit Test: State Transitions**: Kiểm tra flow `PENDING` -> `PROCESSING` (Step X) -> `COMPLETED`.
- [ ] **Integration Test**: Mock API response cho `/documents/upload` với hash trùng lặp.

### Manual E2E Verification
...

1. **Upload Flow:** Mở app → Documents → Upload PDF → Xem polling progress → Toast "Completed"
2. **Chat Flow:** Documents → Chat (doc đã xử lý) → Nhập câu hỏi → Xem SSE streaming → Context chips hiển thị
3. **Graph Flow:** Documents → View Graph → Nodes render → Click node → Sidebar details
4. **Error Flow:** Upload file >50MB → Validation error. Offline network → Error state + Retry

### Performance Targets

- First meaningful paint < 1.5s (dev server)
- Graph render (50 nodes) < 500ms
- SSE first chunk < 3s (backend target)

---

## Timeline ước tính

| Day | Sprint | Nội dung |
|-----|--------|----------|
| Day 1 | 0 + 1 | Backend Readiness, Bootstrap, Design System (P0) |
| Day 2 | 2 + 3 | Data Layer (API, Stores, Hooks), Base Components (P0) |
| Day 3 | 4 + 5 | App Layout, Document Pages (P1) |
| Day 4–6 | 6 | **Chat Interface (P0 - Core Feature)** |
| Day 7–8 | 7 | Graph Viewer (P1) |
| Day 9 | 8 | Polish, Testing, README (P2) |
| Day 10 | Buffer | Dự phòng rủi ro |

---

> [!NOTE]
> **Authentication**: Tạm thời bỏ qua (Skip) cho MVP theo Phase 5 scope. Sẽ được triển khai ở Phase 6 (User Accounts).

---

> [!NOTE]
> Kế hoạch này dựa trên **API Contract đã được xác nhận** từ backend Phase 4 hoàn chỉnh.
> Mọi thay đổi về API response shape cần được thông báo để update TypeScript types tương ứng.
