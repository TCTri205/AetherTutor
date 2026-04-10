# Kế hoạch Tích hợp Obsidian Graph — V2.0 (Optimized)

> **Document Owner:** AetherTutor Team  
> **Created:** April 10, 2026  
> **Last Updated:** April 10, 2026  
> **Status:** Approved (Planning Complete)  
> **Timeline:** Dự kiến 10 tuần (Quý 3 - 2026)  
> **Parent:** [SRS_Overview.md](../srs/SRS_Overview.md), [Module_Contracts.md](../srs/Module_Contracts.md#mc-002-graph-module)

**Changelog V1.0 → V2.0:**
- 🔴 **Critical Fix:** Phân tích root cause — radial layout algorithm tệ hại, KHÔNG phải data issue
- 🔴 **Strategic Change:** Chia 3 giai đoạn (Fix Visual → Import Data → Advanced) thay vì 6 sprints linear
- 🟡 **Option A+B Hybrid:** Dùng `react-force-graph-2d` trước (nhanh), backend spring_layout sau (tối ưu)
- 🟡 **Reprioritize:** Visualization lên P0, Obsidian import xuống Phase 2
- 🟢 **Add:** Root cause analysis, architecture decision records, migration path chi tiết

**Tham chiếu:**
- Obsidian Graph: Wiki-links `[[Note]]`, backlinks, tags, frontmatter, force-directed Canvas layout
- AetherTutor Graph: AI-extracted entities/relations từ PDF, lưu PostgreSQL + ChromaDB
- Gap hiện tại: `calculateRadialLayout` đặt MỌI nodes trên 1 đường tròn → chồng chéo, KHÔNG dùng GraphBuilder

---

## 🔬 ROOT CAUSE ANALYSIS

### Vấn đề: "Graph không ổn" — TẠI SAO?

Sau khi phân tích code (`GraphExplorer.tsx` dòng 113-126), xác định **3 lỗi cốt lõi**:

#### ❌ Lỗi 1: `calculateRadialLayout` — Thuật toán TỆ HẠI

```typescript
// GraphExplorer.tsx:113-126
function calculateRadialLayout(nodesCount: number, centerX: number, centerY: number, radius: number) {
  for (let i = 0; i < nodesCount; i++) {
    const angle = (2 * Math.PI * i) / nodesCount - Math.PI / 2;
    positions.push({
      x: centerX + radius * Math.cos(angle),
      y: centerY + radius * Math.sin(angle),
    });
  }
  return positions;
}
```

**Vấn đề:**
- MỌI nodes được đặt trên **MỘT ĐƯỜNG TRÒN** duy nhất, bán kính cố định 250px
- 50 nodes → 50 nodes trên vòng tròn → **chồng chéo hoàn toàn**
- 100 nodes → Càng tệ hơn
- **KHÔNG có force simulation** → nodes không tự rearrange

**Hệ quả:** Đây CHÍNH LÀ LÝ DO user thấy "graph không ổn"!

---

#### ❌ Lỗi 2: Edge rendering bằng custom SVG path

```tsx
// GraphExplorer.tsx:73-101
const GraphEdge = ({ id, sourceX, sourceY, targetX, targetY, label, style, data }: any) => {
  const midX = (sourceX + targetX) / 2;
  const midY = (sourceY + targetY) / 2;
  // Custom SVG path với cubic bezier
  return (
    <g>
      <path d={`M${sourceX},${sourceY} C${midX},${sourceY} ${midX},${targetY} ${targetX},${targetY}`} ... />
      {label && (
        <g>
          <rect x={midX - 40} y={midY - 10} width={80} height={20} ... />
          <text>{label.length > 15 ? label.slice(0, 15) + '...' : label}</text>
        </g>
      )}
    </g>
  );
};
```

**Vấn đề:**
- Label bị cắt ở 15 ký tự → mất thông tin
- Edge paths tính thủ công → **không phải ReactFlow built-in** → có thể gây lỗi rendering
- SVG-based → performance TỆ với 100+ edges (mỗi edge = DOM element riêng)

---

#### ❌ Lỗi 3: Backend KHÔNG gửi layout positions

```python
# app/api/graph.py:68-82
nodes = [
    GraphNodeView(
        id=e.canonical_name,
        label=e.canonical_name,
        type=e.entity_type,
        description=e.description
        # ❌ KHÔNG CÓ x, y coordinates!
    ) for e in entities
]
```

**Vấn đề:**
- Backend chỉ trả về nodes/edges RAW, KHÔNG có layout positions
- Frontend PHẢI tự tính toán layout → dẫn đến radial layout tệ hại
- **GraphBuilder đã có `get_centrality_scores()`, `detect_communities()` nhưng KHÔNG được expose qua API!**

---

### ✅ Kết luận

**Graph "không ổn" KHÔNG phải do thiếu data — mà do VISUALIZATION TỆ!**

User cần graph ĐẸP và HOẠT ĐỘNG được NGAY, rồi mới tính đến import thêm data từ Obsidian.

---

## 🎯 MỤC TIÊU (GOALS)

### Vấn đề cần giải quyết

| Vấn đề | Root Cause | Priority |
|--------|-----------|----------|
| **Layout xấu** (vòng tròn, nodes chồng) | `calculateRadialLayout` algorithm | 🔴 **P0** |
| **Edge render lỗi** (label bị cắt) | Custom SVG path, giới hạn 15 chars | 🔴 P0 |
| **Giật lag với nhiều nodes** | SVG-based (ReactFlow), không có canvas | 🟡 P1 |
| **Không có backlinks** | Chưa implement backlink system | 🟡 P1 |
| **Graph chỉ từ PDF** | Chưa có Obsidian import | 🟢 P2 |
| **Không có tags/filter** | Chưa có tag system | 🟢 P2 |

### Obsidian làm gì tốt mà ta học hỏi?

| Tính năng Obsidian | Cách hoạt động | Áp dụng vào AetherTutor | Phase |
|-------------------|----------------|------------------------|-------|
| **Force-directed layout** | Force physics simulation (Canvas) | Dùng `react-force-graph-2d` hoặc backend `spring_layout` | Phase 1 |
| **Wiki-links** | `[[Note]]` → tạo edge thủ công | Parse links từ markdown notes | Phase 2 |
| **Backlinks panel** | Hiển thị notes nào link đến đây | Thêm backlinks vào entity sidebar | Phase 2 |
| **Graph view** | Force-directed layout, filter by tag | Cải thiện visualization + filters | Phase 1-3 |
| **Tags** | `#topic` group notes | Thêm tag system cho entities | Phase 2 |
| **Properties (YAML)** | Metadata có cấu trúc | Dùng cho entity metadata | Phase 2 |
| **Local-first** | 100% local, không cloud | Tuân thủ BR-008 (Local Mode) | All phases |

### Key Outcomes

**Phase 1 (Fix Visual):**
- ✅ Force-directed layout (như Obsidian)
- ✅ Edge rendering đúng, label không bị cắt
- ✅ Hover highlight (Obsidian-style)
- ✅ Performance tốt với 100+ nodes

**Phase 2 (Import Data):**
- ✅ Import Obsidian vault → xây dựng graph từ markdown files + wiki-links
- ✅ Entity resolution giữa PDF-extracted entities và Obsidian notes
- ✅ Backlinks system cho entities
- ✅ Tag-based filtering

**Phase 3 (Advanced):**
- ✅ Fix GraphBuilder → integrate vào pipeline chính
- ✅ Global graph explorer (cross-document)
- ✅ Frontend hoàn thiện (search, filter, export)
- ✅ Centrality/community detection expose qua API

### OUT of scope (để Post-MVP)

- ❌ Obsidian plugin (AetherTutor Obsidian plugin)
- ❌ Real-time file watcher + auto-sync (dùng manual import trước)
- ❌ Export AetherTutor graph → Obsidian vault
- ❌ Conflict resolution UI cho PDF vs Notes mâu thuẫn

---

## 📋 PRE-REQUISITES & RÀNG BUỘC KỸ THUẬT

### 2.1 Dependencies từ Sprints trước

| # | Dependency | Trạng thái | Ghi chú |
|---|-----------|-----------|---------|
| **D1** | LightRAG Pipeline | ✅ Done | Entity extraction, graph construction |
| **D2** | PostgreSQL graph tables | ✅ Done | `graph_entities`, `graph_relations`, `entity_aliases` |
| **D3** | NetworkX GraphBuilder | ⚠️ Tồn tại nhưng **KHÔNG dùng trong pipeline** | Cần fix ở Phase 3 |
| **D4** | ReactFlow GraphExplorer | ✅ Done | Radial layout (TỆ), custom nodes/edges |
| **D5** | Entity alias service | ✅ Done | Alias resolution, fuzzy matching |
| **D6** | ARQ Workers | ✅ Done | Background processing |
| **D7** | Graph API endpoints | ✅ Done | `/view`, `/stats`, `/query`, `/global`, aliases |
| **D8** | Frontend graph service | ⚠️ Chỉ 3 methods | Thiếu global/alias/multi-doc |

### 2.2 Ràng buộc kỹ thuật

| Ràng buộc | Giá trị | Impact |
|-----------|---------|--------|
| **User isolation** | BR-001 🔴 | Mọi import/query PHẢI filter theo `user_id` |
| **Local Mode** | BR-008 🔴 | Khi bật local mode, KHÔNG được đọc vault nếu vault trên cloud |
| **Graph consistency** | BR-003 🔴 | Tối thiểu 1 entity trước khi build graph |
| **API response time** | < 500ms P95 | Import operation chạy background, API trả về job ID |
| **RAM giới hạn** | 8GB (CPU-only) | Vault scanning phải nhẹ, không load toàn bộ vào RAM |

---

## 🏗️ KIẾN TRÚC TÍCH HỢP

### 3.1 Data Flow

```mermaid
graph TD
    subgraph Phase 1: Fix Visualization
        A[Backend: PostgreSQL] -->|nodes/edges RAW| B[Backend: spring_layout NetworkX]
        B -->|positions x,y| C[Frontend: react-force-graph-2d]
        C -->|Force simulation| D[Canvas rendering]
        D --> E[Obsidian-like graph]
    end
    
    subgraph Phase 2: Import Data
        F[Obsidian Vault .md files] --> G[ObsidianVaultImporter]
        G --> H[Parse Markdown + Frontmatter]
        H --> I[Extract Wiki-Links [[...]]]
        H --> J[Extract Tags #...]
        I --> K[Build Relations từ links]
        J --> L[Add Tags to Entities]
        K --> M[Entity Resolution Service]
        L --> M
    end
    
    subgraph Phase 3: Advanced
        N[PDF Documents] --> O[LightRAG Pipeline]
        O --> P[AI-extracted Entities/Relations]
        P --> M
        M --> Q[Merge & Deduplicate]
        Q --> R[(PostgreSQL)]
        Q --> S[NetworkX GraphBuilder]
        S -->|centrality, communities| B
        R --> T[Graph API]
        S --> T
        T --> C
    end
```

### 3.2 Components mới

| Component | File | Phase | Responsibility |
|-----------|------|-------|----------------|
| **MarkdownParser** | `app/core/markdown_parser.py` | 2 | Parse .md files, extract frontmatter, links, tags |
| **ObsidianVaultImporter** | `app/services/obsidian_vault_importer.py` | 2 | Scan vault, parse markdown, extract links |
| **EntityResolutionService** | `app/services/entity_resolution_service.py` | 2 | Resolve conflicts giữa PDF entities và Obsidian notes |
| **BacklinkService** | `app/services/backlink_service.py` | 2 | Compute và cache backlinks cho entities |
| **TagService** | `app/services/tag_service.py` | 2 | Tag management cho entities |
| **GraphLayoutService** | `app/core/graph_layout_service.py` | 1-3 | Force-directed layout, centrality-based positioning |

### 3.3 Database Schema Changes

**Thêm columns mới:**

```sql
-- Table: graph_entities
ALTER TABLE graph_entities ADD COLUMN source VARCHAR(50) DEFAULT 'ai_extracted';
-- Values: 'ai_extracted', 'obsidian_import', 'manual', 'merged'

ALTER TABLE graph_entities ADD COLUMN tags TEXT[] DEFAULT '{}';
-- PostgreSQL array cho tags

ALTER TABLE graph_entities ADD COLUMN file_path VARCHAR(500);
-- Path đến file .md trong vault (nếu từ Obsidian)

ALTER TABLE graph_entities ADD COLUMN metadata JSONB DEFAULT '{}';
-- Flexible metadata từ frontmatter

-- Table: graph_relations
ALTER TABLE graph_relations ADD COLUMN source VARCHAR(50) DEFAULT 'ai_extracted';
-- Values: 'ai_extracted', 'obsidian_link', 'manual', 'merged'

ALTER TABLE graph_relations ADD COLUMN is_backlink BOOLEAN DEFAULT FALSE;
-- True nếu đây là backlink (reverse relation)

-- Index mới
CREATE INDEX idx_graph_entities_source ON graph_entities(user_id, source);
CREATE INDEX idx_graph_entities_tags ON graph_entities USING GIN(user_id, tags);
CREATE INDEX idx_graph_relations_source ON graph_relations(source, source);
```

**Migration file:** `alembic/versions/YYYY_MM_DD_obsidian_graph_integration.py`

---

## 🚀 LỘ TRÌNH TRIỂN KHAI CHI TIẾT

### ARCHITECTURE DECISION: Visualization Library

**Quyết định:** Phase 1 dùng `react-force-graph-2d`, Phase 3 evaluate chuyển sang backend spring_layout

| Tiêu chí | **Option A: react-force-graph-2d** | **Option B: Backend spring_layout** |
|----------|-----------------------------------|-------------------------------------|
| **Thời gian** | 1-2 ngày (swap library) | 2-3 ngày (modify backend + frontend) |
| **Performance** | Canvas rendering, tốt cho 1000+ nodes | JSON positions, tốt cho 200 nodes |
| **Interactivity** | Built-in zoom/pan/hover, drag nodes | Phải implement drag + re-layout |
| **Obsidian-like** | ✅ GIỐNG OBSIDIAN (cùng force physics) | ❌ Static positions từ backend |
| **Reusability** | ❌ Phải maintain thêm library | ✅ Tái dụng NetworkX đã có |
| **Complexity** | Thấp (1 component mới) | Trung bình (modify pipeline) |
| **Risk** | Thấp (chỉ thay frontend) | Trung bình (chạm backend pipeline) |

**Kết luận:** Phase 1 dùng Option A (nhanh, đẹp), Phase 3 evaluate Option B (tối ưu)

---

### GIAI ĐOẠN 1: FIX VISUALIZATION (Tuần 1-2) — PRIORITY P0

*Mục tiêu: Graph phải ĐẸP và HOẠT ĐỘNG được NGAY, như Obsidian*

#### Sprint 1: Force-Directed Layout & Canvas Rendering (3-5 ngày)

| # | Task | File(s) | Độ phức tạp | Thời lượng |
|---|------|---------|-------------|-----------|
| **B1** | **Install `react-force-graph-2d`** | `frontend/package.json` | Low | 0.5h |
|   | - `npm install react-force-graph-2d d3-force` | | | |
|   | - Kiểm tra TypeScript compatibility | | | |
| **B2** | **Replace ReactFlow với ForceGraph2D** | `frontend/src/pages/GraphExplorer.tsx` | High | 6h |
|   | - Gỡ bỏ imports ReactFlow, `calculateRadialLayout` | | | |
|   | - Tích hợp `<ForceGraph2D>` component | | | |
|   | - Config forces: `d3.forceManyBody()` (charge), `d3.forceLink()` (pull), `d3.forceCenter()` | | | |
|   | - Node rendering: `nodeCanvasObject` — vẽ circles + labels theo entity_type | | | |
|   | - Edge rendering: `linkCanvasObject` — vẽ arrows với labels | | | |
|   | - Giữ node click → mở GraphSidebar | | | |
| **B3** | **Hover Highlight (Obsidian-style)** | `frontend/src/pages/GraphExplorer.tsx` | Medium | 3h |
|   | - `onNodeHover` → highlight connected nodes/edges, dim others | | | |
|   | - Tooltip hiển thị entity name + type | | | |
| **B4** | **Node Click → Sidebar** | `frontend/src/pages/GraphExplorer.tsx` | Low | 2h |
|   | - `onNodeClick` → mở GraphSidebar với entity details | | | |
|   | - Fetch neighbors từ backend (nếu cần) | | | |
| **B5** | **Edge Label Rendering** | `frontend/src/pages/GraphExplorer.tsx` | Medium | 3h |
|   | - Hiển thị FULL label (không cắt 15 chars) | | | |
|   | - Labels chỉ hiện khi zoom đủ gần (để tránh clutter) | | | |
| **B6** | **Performance Test** | Manual testing | Low | 1h |
|   | - Test với 50, 100, 200 nodes | | | |
|   | - Measure FPS, memory usage | | | |
| **B7** | **Unit Tests** | `tests/unit/test_graph_explorer.py` | Medium | 2h |
|   | - Test graph data transformation | | | |
|   | - Test highlight logic | | | |

**Acceptance Criteria:**
- [ ] Force-directed layout hoạt động, nodes không chồng chéo
- [ ] Hover highlight như Obsidian (connected nodes sáng, others mờ)
- [ ] Click node → mở sidebar với details
- [ ] Edge labels hiển thị đầy đủ, không bị cắt
- [ ] Performance: 60 FPS với 100 nodes trên Canvas
- [ ] Tests pass ≥ 90% coverage

---

#### Sprint 1.5: Backend Layout Enhancement (2-3 ngày) — Optional

*Task này OPTIONAL — chỉ làm nếu muốn positions chính xác hơn từ backend*

| # | Task | File(s) | Độ phức tạp | Thời lượng |
|---|------|---------|-------------|-----------|
| **B8** | **Expose centrality scores qua API** | `app/api/graph.py` | Low | 2h |
|   | - `GET /api/v1/graph/{doc_id}/centrality` | | | |
|   | - Dùng GraphBuilder `get_centrality_scores()` | | | |
|   | - Response: `{entity_name, degree_centrality, betweenness, closeness}` | | | |
| **B9** | **Add positions vào response** | `app/api/graph.py` | Medium | 3h |
|   | - Dùng `networkx.spring_layout()` tính positions | | | |
|   | - Gửi kèm `{x, y}` trong nodes response | | | |
|   | - Frontend dùng làm initial positions (force simulation sẽ adjust) | | | |
| **B10** | **Add community detection vào response** | `app/api/graph.py` | Low | 2h |
|   | - Dùng GraphBuilder `detect_communities()` | | | |
|   | - Gửi `community_id` per node → frontend color-code | | | |

**Acceptance Criteria:**
- [ ] API trả về centrality scores
- [ ] API có thể gửi positions (optional)
- [ ] Community detection hoạt động

---

### GIAI ĐOẠN 2: OBSIDIAN IMPORT (Tuần 3-5) — PRIORITY P1

*Mục tiêu: Import Obsidian vault → graph có thêm data từ notes*

#### Sprint 2: Obsidian Vault Importer Core (2 tuần)

| # | Task | File(s) | Độ phức tạp | Thời lượng |
|---|------|---------|-------------|-----------|
| **B11** | **Implement MarkdownParser** | `app/core/markdown_parser.py` | Medium | 4h |
|   | - `parse_file(file_path: Path) → ParsedNote` | | | |
|   | - Extract frontmatter (YAML) → `dict` | | | |
|   | - Extract wiki-links `[[Note Name]]` → `List[str]` | | | |
|   | - Extract tags `#tag` → `List[str]` | | | |
|   | - Handle edge cases: aliases `[[Note\|Alias]]`, embeds `![[image]]` | | | |
| **B12** | **Implement ObsidianVaultImporter** | `app/services/obsidian_vault_importer.py` | High | 6h |
|   | - `scan_vault(vault_path: Path, user_id: UUID) → ImportResult` | | | |
|   | - Đệ quy qua vault directory, bỏ `.obsidian/`, `.git/` | | | |
|   | - Parse từng `.md` file qua MarkdownParser | | | |
|   | - Build entities từ notes (mỗi note = 1 entity type 'note') | | | |
|   | - Build relations từ wiki-links (source → target, type 'links_to') | | | |
|   | - Deduplicate entities by canonical_name (case-insensitive) | | | |
|   | - Call `graph_repo.bulk_upsert_entities()` và `bulk_upsert_relations()` | | | |
| **B13** | **API Endpoint** | `app/api/graph.py` | Low | 2h |
|   | - `POST /api/v1/graph/import/obsidian` | | | |
|   | - Request: `{vault_path: str}` | | | |
|   | - Response: `202 Accepted` với `job_id` (async import) | | | |
| **B14** | **ARQ Worker Task** | `app/worker/tasks.py` | Medium | 3h |
|   | - `import_obsidian_vault_task(job_id, vault_path, user_id)` | | | |
|   | - Progress tracking qua Redis key `import:{job_id}:progress` | | | |
| **B15** | **Schemas** | `app/schemas/graph.py` | Low | 1h |
|   | - `ObsidianImportRequest {vault_path: str}` | | | |
|   | - `ImportJobStatus {job_id, status, progress, result, error}` | | | |
| **B16** | **Unit Tests** | `tests/unit/test_obsidian_importer.py` | Medium | 3h |
|   | - Test parse wiki-links variants, frontmatter extraction | | | |
|   | - Test vault scanning với mock files | | | |

**Acceptance Criteria:**
- [ ] Import thành công vault 100 notes với wiki-links
- [ ] Entities và relations xuất hiện trong PostgreSQL
- [ ] Frontend ForceGraph2D hiển thị được nodes mới
- [ ] Tests pass ≥ 90% coverage

---

#### Sprint 3: Entity Resolution & Merge (1 tuần)

| # | Task | File(s) | Độ phức tạp | Thời lượng |
|---|------|---------|-------------|-----------|
| **B17** | **Implement EntityResolutionService** | `app/services/entity_resolution_service.py` | High | 6h |
|   | - `resolve_conflicts(pdf_entities, obsidian_entities, user_id) → MergedResult` | | | |
|   | - Strategy 1: Exact match on `canonical_name` (case-insensitive) → merge | | | |
|   | - Strategy 2: Fuzzy match (SequenceMatcher ≥ 0.85) → suggest merge | | | |
|   | - Strategy 3: LLM verify cho ambiguous cases | | | |
| **B18** | **API Endpoint cho Conflict Resolution** | `app/api/graph.py` | Medium | 3h |
|   | - `POST /api/v1/graph/entities/resolve-conflicts` | | | |
| **B19** | **Unit Tests** | `tests/unit/test_entity_resolution.py` | Medium | 3h |

**Acceptance Criteria:**
- [ ] Entities trùng lặp được merge tự động
- [ ] Fuzzy match gợi ý đúng các entities tương tự
- [ ] API conflict resolution hoạt động

---

#### Sprint 4: Backlinks & Tags System (1 tuần)

| # | Task | File(s) | Độ phức tạp | Thời lượng |
|---|------|---------|-------------|-----------|
| **B20** | **Implement BacklinkService** | `app/services/backlink_service.py` | Medium | 4h |
|   | - `get_backlinks(entity_id, user_id) → List[Backlink]` | | | |
|   | - Cache vào Redis (TTL 1h) | | | |
| **B21** | **Implement TagService** | `app/services/tag_service.py` | Low | 2h |
|   | - `get_tags()`, `get_entities_by_tag()`, `add_tags()` | | | |
| **B22** | **API Endpoints** | `app/api/graph.py` | Low | 2h |
|   | - `GET /graph/entities/{id}/backlinks` | | | |
|   | - `GET /graph/tags`, `GET /graph/tags/{tag}/entities` | | | |
| **B23** | **Frontend: Backlinks Panel** | `frontend/src/components/graph/BacklinksPanel.tsx` | Medium | 3h |
| **B24** | **Frontend: Tag Filter** | `frontend/src/components/graph/TagFilter.tsx` | Low | 2h |

**Acceptance Criteria:**
- [ ] Backlinks panel hiển thị trong sidebar
- [ ] Tag filter hoạt động trên graph view
- [ ] API endpoints trả về đúng data

---

### GIAI ĐOẠN 3: ADVANCED FEATURES (Tuần 6-10) — PRIORITY P2

#### Sprint 5: GraphBuilder Integration (1 tuần)

| # | Task | File(s) | Độ phức tạp | Thời lượng |
|---|------|---------|-------------|-----------|
| **B25** | **Integrate GraphBuilder vào Pipeline** | `app/core/pipeline.py` | Medium | 3h |
|   | - Sau khi upsert entities/relations, gọi `GraphBuilder.add_entities_and_relations()` | | | |
|   | - Call `GraphBuilder.persist_graph(doc_id)` để export GraphML + JSON | | | |
| **B26** | **Database Migration** | `alembic/versions/...` | Low | 2h |
|   | - Thêm columns: `source`, `tags[]`, `file_path`, `metadata` | | | |

**Acceptance Criteria:**
- [ ] GraphBuilder được gọi trong pipeline
- [ ] GraphML files được tạo ra trong `/uploads/graphs/`

---

#### Sprint 6: Global Graph Explorer (2 tuần)

| # | Task | File(s) | Độ phức tạp | Thời lượng |
|---|------|---------|-------------|-----------|
| **B27** | **Frontend: Global Graph Explorer** | `frontend/src/pages/GlobalGraphExplorer.tsx` | High | 6h |
|   | - Clone GraphExplorer, dùng `/graph/global` endpoint | | | |
|   | - Aggregate nodes by canonical_name across docs | | | |
| **B28** | **Frontend: Entity Alias UI** | `frontend/src/components/graph/AliasManager.tsx` | Medium | 4h |
| **B29** | **Frontend: Multi-doc Query UI** | `frontend/src/components/graph/MultiDocQuery.tsx` | Medium | 4h |

**Acceptance Criteria:**
- [ ] Global graph explorer hiển thị đúng
- [ ] Alias UI hoạt động CRUD
- [ ] Multi-doc query UI hoạt động

---

#### Sprint 7: Frontend Polish (2 tuần)

| # | Task | File(s) | Độ phức tạp | Thời lượng |
|---|------|---------|-------------|-----------|
| **B30** | **Enhanced Nodes: tags, source badges** | `frontend/src/components/graph/EntityNode.tsx` | Medium | 3h |
| **B31** | **Enhanced Edges: color-code by relation_type** | `frontend/src/components/graph/GraphEdge.tsx` | Low | 2h |
| **B32** | **Graph Search Bar (Ctrl+K)** | `frontend/src/components/graph/GraphSearchBar.tsx` | Medium | 3h |
| **B33** | **Export Graph (PNG, SVG, GraphML)** | `frontend/src/components/graph/GraphExport.tsx` | Low | 2h |

**Acceptance Criteria:**
- [ ] Nodes có tag badges và source indicators
- [ ] Edges color-coded
- [ ] Search bar filter đúng
- [ ] Export được nhiều format

---

#### Sprint 8: Testing & Docs (1 tuần)

| # | Task | File(s) | Độ phức tạp | Thời lượng |
|---|------|---------|-------------|-----------|
| **B34** | **Integration Tests** | `tests/integration/test_obsidian_import.py` | Medium | 3h |
| **B35** | **Update SRS Documents** | `docs/srs/Module_Contracts.md` | Low | 2h |
| **B36** | **Update User Flows** | `docs/srs/User_Flows.md` | Low | 2h |
| **B37** | **README & Documentation** | `docs/obsidian_integration/README.md` | Medium | 3h |

**Acceptance Criteria:**
- [ ] Integration tests pass ≥ 90%
- [ ] SRS documents updated
- [ ] README hoàn chỉnh

---

## 📊 TỔNG KẾ THỜI LƯỢNG

| Giai đoạn | Sprint | Thời lượng | Priority |
|-----------|--------|-----------|----------|
| **Phase 1: Fix Visual** | Sprint 1 | 17.5h (3-5 ngày) | 🔴 **P0** |
| | Sprint 1.5 (Optional) | 7h (2 ngày) | 🟡 P1 |
| **Phase 2: Import Data** | Sprint 2-4 | 38h (4 tuần) | 🟡 P1 |
| **Phase 3: Advanced** | Sprint 5-8 | 34h (6 tuần) | 🟢 P2 |
| **TỔNG** | | **96.5h (~10 tuần)** | |

---

## ⚠️ RỦI RO & MITIGATION

| Rủi ro | Impact | Likelihood | Mitigation |
|--------|--------|-----------|-----------|
| **react-force-graph-2d break existing features** | High | Medium | Test kỹ trước khi merge, giữ ReactFlow code trong git branch riêng |
| **Vault quá lớn (>1000 notes)** | High | Medium | Import bất đồng bộ qua ARQ, progress tracking |
| **Entity conflicts quá nhiều** | Medium | Medium | Auto-resolve exact matches, manual review cho fuzzy |
| **Performance degradation** | High | Low | Index mới cho tags, source columns; cache backlinks |
| **Local Mode violation** | Critical | Low | Validate vault path local, check BR-008 compliance |

---

## 🔍 METRICS & SUCCESS CRITERIA

| Metric | Target | Measurement |
|--------|--------|-------------|
| **Phase 1: Layout quality** | Users rate ≥ 4/5 | Survey sau khi release |
| **Phase 1: FPS** | ≥ 60 FPS với 100 nodes | Chrome DevTools Performance tab |
| **Import success rate** | ≥ 95% | Jobs completed / total jobs |
| **Entity resolution accuracy** | ≥ 90% | Correct merges / total merges |
| **API response time (P95)** | < 500ms | Prometheus metrics |
| **Test coverage** | ≥ 85% | pytest-cov report |

---

## 📝 GHI CHÚ IMPLEMENTATION

### Obsidian Wiki-links Parsing Rules

```python
# Patterns cần handle:
"[[Note Name]]"           # Simple link
"[[Note Name|Alias]]"     # Link với display text
"[[Note Name#Heading]]"   # Link to heading
"![[Image.png]]"          # Embed (ignore images)
"[[Note 1]] and [[Note 2]]" # Multiple links
"[text](internal_path.md)" # Markdown links
```

### Entity Source Priority

Khi merge entities từ nhiều sources:
1. **Manual** (user tạo) > **Obsidian** (notes) > **AI** (PDF extraction)
2. Description: keep longest
3. Confidence: keep highest
4. Tags: union của tất cả

### Tag Naming Convention

- Normalize tags: lowercase, strip whitespace, remove `#` prefix
- Deduplicate: `#machine-learning` = `#MachineLearning` = `#machine learning`
- Store: `["machine-learning", "deep-learning", "nlp"]`

---

## 🔗 THAM KHẢO

- [SRS Overview](../srs/SRS_Overview.md)
- [Module Contracts](../srs/Module_Contracts.md) (MC-002: Graph Module)
- [User Flows](../srs/User_Flows.md) (UF-006: Graph Visualization)
- [Business Rules](../srs/Business_Rules.md) (BR-001, BR-003, BR-008, BR-009)
- [Stage 3 Plan](./2026-04-10_stage3_visualization_multimedia.md) (Visualization & Multimedia)
- [Hybrid Entity Extraction](./2026-04-10_hybrid_entity_extraction.md)
- [Gemini Implementation Plan](file:///c:/Users/This%20PC/.gemini/antigravity/brain/bec574c7-3d0a-4809-89b8-f3045d0214f3/implementation_plan.md.resolved)

---

© 2026 AetherTutor Team
