# Obsidian Graph Integration

Tính năng này cho phép bạn tích hợp các ghi chú từ Obsidian Vault vào Bản đồ Tri thức của AetherTutor, kết hợp sức mạnh của việc trích xuất thực thể AI (từ PDF) với ghi chú cá nhân của bạn.

## Tính năng chính

- **Import Obsidian Vault:** Quét toàn bộ ghi chú `.md`, trích xuất frontmatter, wiki-links (`[[Note]]`) và hashtags (`#tag`).
- **Entity Resolution:** Tự động phát hiện và gộp các thực thể trùng tên giữa PDF và Obsidian (exact match + fuzzy match + LLM verification).
- **Manual Merge:** Cho phép gộp thủ công các thực thể tương tự nhau để giữ cho đồ thị gọn gàng.
- **Backlinks:** Hiển thị danh sách các tài liệu/ghi chú trỏ đến thực thể hiện tại ngay trong Graph Sidebar.
- **Tag Filtering:** Lọc đồ thị theo các thẻ (hashtags) được trích xuất từ Obsidian.
- **Global Graph Explorer:** Xem đồ thị tri thức toàn cục跨越 tất cả tài liệu và ghi chú.
- **Export Formats:** Xuất đồ thị dưới dạng PNG, SVG, hoặc GraphML.
- **Force-Directed Layout:** Sử dụng `react-force-graph-2d` cho hiệu ứng vật lý mượt mà giống Obsidian.

## Cách sử dụng

### 1. Import Obsidian Vault
1. Mở **Graph Explorer**.
2. Click vào biểu tượng thư mục (**Import Obsidian Vault**) ở bảng công cụ góc dưới bên phải.
3. Nhập đường dẫn tuyệt đối đến thư mục Obsidian Vault của bạn (ví dụ: `D:\Documents\MyKnowledge`).
4. Hệ thống sẽ chạy tác vụ ngầm để phân tích và đưa dữ liệu vào đồ thị.
5. Theo dõi tiến trình import qua modal status (real-time progress tracking).

### 2. Xem Global Graph
- Truy cập `/global-graph` để xem đồ thị tri thức toàn bộ跨越 tất cả tài liệu.
- Global Graph tổng hợp các entities từ nhiều nguồn (PDF, Obsidian, manual) và hiển thị mối quan hệ chéo.

### 3. Quản lý thực thể (Merge & Aliases)
- Sử dụng bảng **Manage Aliases** (biểu tượng Users) để xem các đề xuất gộp thực thể từ AI.
- Khi gộp (Merge), toàn bộ các liên kết của thực thể cũ sẽ được chuyển hướng sang thực thể mới.
- Entity Resolution tự động chạy khi import, sử dụng 3 levels: exact match → fuzzy match (SequenceMatcher ≥ 0.85) → LLM verification.

### 4. Filtering & Search
- **Tag Filter:** Click vào dropdown tags ở header để lọc entities theo tag.
- **Search (Ctrl+K):** Tìm kiếm nhanh entities bằng tên hoặc description.
- **Combined Filters:** Có thể kết hợp cả tag filter và search query.

### 5. Export Graph
- Click vào biểu tượng **Download** để xuất PNG.
- Click vào biểu tượng **Share** để xuất GraphML.
- Click vào biểu tượng **Download** (thứ 2) để xuất SVG (vector graphics).

### 6. Phím tắt trong Graph View
- **Ctrl + K**: Mở/Đóng thanh tìm kiếm nhanh.
- **Escape**: Đóng các bảng hiện đang mở.
- **Cuộn chuột**: Phóng to/thu nhỏ đồ thị.
- **Kéo chuột**: Di chuyển góc nhìn.
- **Click node**: Mở sidebar với chi tiết thực thể.
- **Hover node**: Highlight connected nodes, dim others.

## Cấu trúc kỹ thuật

### Backend Components

| Component | File | Responsibility |
|-----------|------|----------------|
| **MarkdownParser** | `app/core/markdown_parser.py` | Parse .md files, extract frontmatter, wiki-links, tags |
| **ObsidianVaultImporter** | `app/services/obsidian_vault_importer.py` | Scan vault, orchestrate parsing & import |
| **EntityResolutionService** | `app/services/entity_resolution_service.py` | Resolve & merge duplicate entities |
| **BacklinkService** | `app/services/backlink_service.py` | Compute incoming relations for entities |
| **TagService** | `app/services/tag_service.py` | Tag management & filtering |
| **GraphBuilder** | `app/core/graph_builder.py` | NetworkX graph operations (centrality, communities) |

### Frontend Components

| Component | File | Responsibility |
|-----------|------|----------------|
| **GraphExplorer** | `frontend/src/pages/GraphExplorer.tsx` | Document-level graph visualization |
| **GlobalGraphExplorer** | `frontend/src/pages/GlobalGraphExplorer.tsx` | Cross-document global graph view |
| **TagFilter** | `frontend/src/components/graph/TagFilter.tsx` | Tag selection & filtering UI |
| **GraphSearchBar** | `frontend/src/components/graph/GraphSearchBar.tsx` | Entity search with autocomplete |
| **BacklinksPanel** | `frontend/src/components/graph/BacklinksPanel.tsx` | Display incoming relations |
| **AliasManager** | `frontend/src/components/graph/AliasManager.tsx` | Entity alias resolution UI |
| **MultiDocQuery** | `frontend/src/components/graph/MultiDocQuery.tsx` | Cross-document query interface |

### Database Schema

```sql
-- graph_entities table additions
source VARCHAR(50) DEFAULT 'ai_extracted'  -- 'ai_extracted', 'obsidian_import', 'manual', 'merged'
tags TEXT[] DEFAULT '{}'                   -- PostgreSQL array for tags
file_path VARCHAR(500)                     -- Path to .md file in vault
metadata JSONB DEFAULT '{}'                -- Flexible metadata from frontmatter

-- graph_relations table additions
source VARCHAR(50) DEFAULT 'ai_extracted'  -- 'ai_extracted', 'obsidian_link', 'manual', 'merged'
is_backlink BOOLEAN DEFAULT FALSE          -- True if this is a reverse relation
```

### API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/graph/import/obsidian` | Start Obsidian vault import (async) |
| GET | `/api/v1/graph/import/obsidian/status/{job_id}` | Check import job status |
| GET | `/api/v1/graph/{doc_id}/centrality` | Get centrality scores (degree, betweenness, closeness) |
| GET | `/api/v1/graph/entities/{entity_id}/backlinks` | Get incoming relations for entity |
| GET | `/api/v1/graph/tags` | Get all tags used by user |
| GET | `/api/v1/graph/tags/{tag}/entities` | Get entities with specific tag |
| POST | `/api/v1/graph/global` | Get global graph across documents |

### Data Flow

```
Obsidian Vault (.md files)
  ↓
MarkdownParser (extract frontmatter, wiki-links, tags)
  ↓
EntityResolutionService (resolve duplicates, merge data)
  ↓
GraphRepository (upsert to PostgreSQL)
  ↓
GraphBuilder (update NetworkX graph, persist GraphML)
  ↓
Graph API (serve to frontend)
  ↓
ForceGraph2D (canvas rendering with force simulation)
```

## Testing

### Unit Tests
```bash
# Test Obsidian importer
pytest tests/unit/test_obsidian_importer.py

# Test entity resolution
pytest tests/unit/test_entity_resolution.py

# Test graph builder
pytest tests/unit/test_graph_builder.py
```

### Integration Tests
```bash
# Test full import workflow
pytest tests/integration/test_obsidian_import.py

# Test graph API endpoints
pytest tests/integration/test_graph_api.py
```

### Frontend Tests
```bash
# Test GraphExplorer component
cd frontend && npm run test
```

## Known Limitations

1. **Local Vault Only:** Chỉ hỗ trợ vault local (theo BR-008 Local Mode). Không hỗ trợ vault trên cloud/remote.
2. **Manual Import:** Không có file watcher/auto-sync. Phải trigger import thủ công.
3. **No Export to Obsidian:** Hiện tại chỉ import từ Obsidian, chưa có chiều ngược lại.
4. **Image Embeds:** `![[image.png]]` được bỏ qua, chỉ xử lý wiki-links text.

## Future Enhancements (Post-MVP)

- [ ] Obsidian Plugin (AetherTutor Obsidian plugin)
- [ ] Real-time file watcher + auto-sync
- [ ] Export AetherTutor graph → Obsidian vault
- [ ] Conflict resolution UI cho PDF vs Notes mâu thuẫn
- [ ] Graph diff & versioning

---
© 2026 AetherTutor Team

