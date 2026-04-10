# Kế hoạch triển khai Hybrid Entity Extraction (Tối ưu 8GB RAM) — V2.4

Hệ thống hiện tại đang phụ thuộc hoàn toàn vào LLM lớn để trích xuất, gây quá tải cho cấu hình CPU-only 8GB RAM.
Giải pháp Hybrid này tối ưu hóa bộ nhớ bằng cách kết hợp spaCy (nhanh, nhẹ) + LLM fallback (chính xác, chỉ khi cần).

**Changelog V2.3 → V2.4:**
- 🔴 **Fix blocking:** Thêm section **4. Pipeline Integration** với code cụ thể — pipeline truyền `List[str]` thay vì `str` cho extractor.
- 🔴 **Fix blocking:** Spec đầy đủ `_extract_llm_batch()` — dùng lại prompt + schema hiện tại của `extract()`.
- 🟡 **Fix magic number:** Thay `i*5` bằng `i * ENTITY_EXTRACTION_BATCH_SIZE`.
- 🟡 **Fix merge code:** Thêm pseudocode đầy đủ cho `_merge_results()` với `rel.source`/`rel.target` (không phải `source_id`).
- 🟡 **Fix type mapping:** Thêm lại `SPACY_TO_STANDARD_TYPES` vào `fast_extractor.py`.
- 🟡 **Fix constants placement:** Chuyển `ENTITY_EXTRACTION_METHOD` sang `config.py` (đúng design).
- 🟢 **Fix return type:** Giữ `Optional[ExtractionResult]` cho backward compat.
- 📝 **Fix model name:** Sửa lại đúng model thực tế `hf.co/Qwen/Qwen2.5-1.5B-Instruct-GGUF:Q4_K_M` (Ollama).

---

## 🔍 PHÂN TÍCH THỰC TRẠNG

### Hiện tại (Pipeline đang chạy)
| Thành phần | Trạng thái |
|-----------|-----------|
| **Entity Extraction** | LLM 100% (Qwen2.5-1.5B GGUF Q4_K_M) |
| **Worker Timeout** | 1800s (30 phút) |
| **Batch Size** | `ENTITY_EXTRACTION_BATCH_SIZE = 5` (trong `constants.py`) |
| **RAM Usage** | ~1.2GB cho Ollama (Qwen2.5-1.5B) + ~0.5GB cho app |
| **EntityExtractor.extract()** | Nhận `text: str`, gọi `llm_service.structured_extraction(prompt, ExtractionResult)` |

### Vấn đề cần giải quyết
1. **LLM gọi quá nhiều lần** — mỗi batch 5 chunks = 1 LLM call, document lớn có thể 40+ calls
2. **Không có fallback** — nếu LLM fail, không có entity nào
3. **Relations extraction phụ thuộc hoàn toàn vào LLM** — cần đảm bảo luôn có ít nhất 1 batch LLM chạy
4. **Không có config toggle** — không thể switch phương pháp trích xuất

---

## 🏗️ KIẾN TRÚC HYBRID (V2.4)

```text
Document Chunks (từ pipeline)
      ↓
┌───────────────────────────────────────┐
│ Bước 1: Fast Extractor (spaCy)        │ ← Toàn bộ text gộp lại (~1-2s, ~50MB RAM)
│ - NER: PERSON, ORG, GPE, PRODUCT...   │
│ - Type mapping → hệ thống chuẩn        │
└──────────────┬────────────────────────┘
               ↓
┌───────────────────────────────────────┐
│ Bước 2: Mandatory LLM Batch (Batch #1)│ ← LUÔN CHẠY để lấy Relations
│ - 5 chunks đầu (ENTITY_EXTRACTION...  │
│ - Entities + Relations quality cao    │
└──────────────┬────────────────────────┘
               ↓
      Đã đủ Entities chưa? (≥ 30)
         ↓               ↓
      RỒI (Dừng)      CHƯA (Tiếp tục)
         ↓               ↓
    ┌────┴────┐    ┌────────────────────────────────────────┐
    │  Merge  │    │ LLM Fallback Loop (Batch #2 → #10)     │
    └─────────┘    │ - Chỉ chạy nếu thiếu thực thể          │
                   │ - Giới hạn ENTITY_EXTRACTION_MAX_...   │
                   │ - try/except từng batch                │
                   └──────────────────┬─────────────────────┘
                                      ↓
                        Merge + Dedup + Confidence Max
                                      ↓
                               Knowledge Graph
```

---

## 📝 CHI TIẾT THAY ĐỔI

### 1. Cấu hình & Constants

#### [MODIFY] `app/constants.py`
Thêm 2 constants nội bộ (**KHÔNG duplicate sang config.py/env**):
```python
# Hybrid Entity Extraction
ENTITY_EXTRACTION_MIN_ENTITIES = 30       # Ngưỡng dừng fallback LLM
ENTITY_EXTRACTION_MAX_LLM_BATCHES = 10    # Giới hạn LLM calls tối đa
```

#### [MODIFY] `app/config.py`
Thêm setting phương pháp vào Settings class:
```python
# Entity Extraction
ENTITY_EXTRACTION_METHOD: str = "hybrid"  # "llm" | "hybrid" | "spacy_only"
```

#### [MODIFY] `.env.example`
```env
# Entity Extraction
ENTITY_EXTRACTION_METHOD=hybrid  # llm | hybrid | spacy_only
```

---

### 2. Core Components

#### [NEW] `app/core/fast_extractor.py`
Tạo lớp `FastExtractor` với **Thread-safe Singleton** và **Type Mapping** chuẩn hóa spaCy labels → hệ thống types:

```python
"""
Fast Entity Extractor — spaCy
Dùng để extract entities NHANH (không cần LLM).
"""
import spacy
import threading
import logging
from typing import List
from ..schemas.lightrag import ExtractedEntity, ExtractionResult

logger = logging.getLogger(__name__)

# Map spaCy NER labels → hệ thống entity types chuẩn
SPACY_TO_STANDARD_TYPES = {
    "PERSON": "PERSON",
    "ORG": "ORGANIZATION",
    "GPE": "LOCATION",
    "LOC": "LOCATION",
    "PRODUCT": "TECHNOLOGY",
    "WORK_OF_ART": "CONCEPT",
    "EVENT": "EVENT",
    "LAW": "CONCEPT",
    "LANGUAGE": "CONCEPT",
    "NORP": "CONCEPT",
    "FAC": "LOCATION",
    "MONEY": "CONCEPT",
    "QUANTITY": "CONCEPT",
    "DATE": "CONCEPT",
    "TIME": "CONCEPT",
    "PERCENT": "CONCEPT",
    "ORDINAL": "CONCEPT",
    "CARDINAL": "CONCEPT",
}

class FastExtractor:
    """Thread-safe Singleton cho Model spaCy (~50MB)"""
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                try:
                    cls._instance._nlp = spacy.load("en_core_web_sm")
                    logger.info("spaCy model 'en_core_web_sm' loaded successfully")
                except OSError as e:
                    logger.error(
                        "spaCy model 'en_core_web_sm' not found. "
                        "Install with: python -m spacy download en_core_web_sm"
                    )
                    raise RuntimeError(
                        "spaCy model required for FastExtractor is missing. "
                        "Run: python -m spacy download en_core_web_sm"
                    ) from e
        return cls._instance

    def extract(self, text: str) -> ExtractionResult:
        """Extract entities từ text bằng spaCy"""
        doc = self._nlp(text)

        entities = []
        for ent in doc.ents:
            standard_type = SPACY_TO_STANDARD_TYPES.get(ent.label_, "CONCEPT")
            entities.append(ExtractedEntity(
                name=ent.text.strip().title(),
                entity_type=standard_type,
                description=f"{ent.label_} entity extracted from context",
                confidence=0.8
            ))

        # spaCy không trích xuất relations chất lượng cho technical docs
        relations = []

        return ExtractionResult(entities=entities, relations=relations)
```

---

### 3. Entity Extractor (Cập nhật V2.4)

#### [MODIFY] `app/core/entity_extractor.py`

**Thay đổi chính:**
1. `extract()` nhận **`chunks: List[str]`** thay vì `text: str`
2. Thêm `__init__` nhận `config` để toggle method
3. Thêm `_extract_llm_batch()` — spec chi tiết bên dưới
4. Thêm `_merge_results()` — pseudocode đầy đủ với schema đúng

```python
"""
Entity Extractor — Hybrid (spaCy + LLM fallback)
"""
from typing import List, Optional
from ..schemas.lightrag import ExtractionResult, ExtractedEntity, EntityRelation
from ..services.llm_service import llm_service
from ..constants import (
    ENTITY_EXTRACTION_BATCH_SIZE,
    ENTITY_EXTRACTION_MIN_ENTITIES,
    ENTITY_EXTRACTION_MAX_LLM_BATCHES,
)

class EntityExtractor:
    """
    Hybrid entity extractor:
    - Fast layer: spaCy (entities only)
    - Fallback layer: LLM (entities + relations, batch-by-batch)
    """

    def __init__(self, aliases: dict = None, config=None):
        self.aliases = aliases or {}
        self._config = config

        # Lazy-init FastExtractor chỉ khi cần
        method = getattr(config, "ENTITY_EXTRACTION_METHOD", "llm") if config else "llm"
        if method in ("hybrid", "spacy_only"):
            from .fast_extractor import FastExtractor
            self._fast_extractor = FastExtractor()
        else:
            self._fast_extractor = None

    def _normalize_name(self, name: str) -> str:
        clean_name = name.strip().lower()
        if clean_name in self.aliases:
            return self.aliases[clean_name]
        return name.strip().title()

    # ============================================================
    # Public API — signature thay đổi: nhận List[str] thay vì str
    # ============================================================

    async def extract(self, chunks: List[str]) -> Optional[ExtractionResult]:
        """
        Extract entities & relations từ danh sách chunks.

        Args:
            chunks: List of text chunks (đã được chunk từ pipeline)

        Returns:
            ExtractionResult hoặc None (nếu spacy_only và fail)
        """
        method = getattr(self._config, "ENTITY_EXTRACTION_METHOD", "llm") if self._config else "llm"

        if method == "spacy_only":
            return await self._extract_spacy_only(chunks)
        elif method == "hybrid":
            return await self._extract_hybrid(chunks)
        else:  # "llm" — giữ nguyên logic cũ
            return await self._extract_llm_legacy(chunks)

    # ============================================================
    # Legacy LLM mode (giữ backward compat)
    # ============================================================

    async def _extract_llm_legacy(self, chunks: List[str]) -> Optional[ExtractionResult]:
        """Logic cũ: gọi LLM cho từng batch, gộp kết quả."""
        all_entities = []
        all_relations = []
        total_batches = max(1, (len(chunks) + ENTITY_EXTRACTION_BATCH_SIZE - 1) // ENTITY_EXTRACTION_BATCH_SIZE)

        for i in range(total_batches):
            batch = chunks[i * ENTITY_EXTRACTION_BATCH_SIZE : (i + 1) * ENTITY_EXTRACTION_BATCH_SIZE]
            combined = "\n\n---\n\n".join(batch)
            result = await self._extract_llm_batch(combined)
            if result:
                all_entities.extend(result.entities)
                all_relations.extend(result.relations)

        if not all_entities and not all_relations:
            return None

        return ExtractionResult(entities=all_entities, relations=all_relations)

    # ============================================================
    # spaCy-only mode
    # ============================================================

    async def _extract_spacy_only(self, chunks: List[str]) -> Optional[ExtractionResult]:
        full_text = " ".join(chunks)
        result = self._fast_extractor.extract(full_text)
        # Normalize names
        for ent in result.entities:
            ent.name = self._normalize_name(ent.name)
        return result

    # ============================================================
    # Hybrid mode (MỚI — V2.4)
    # ============================================================

    async def _extract_hybrid(self, chunks: List[str]) -> Optional[ExtractionResult]:
        """
        Hybrid extraction:
        1. Fast extract toàn bộ text bằng spaCy
        2. Mandatory LLM batch #1 — LUÔN CHẠY để lấy relations
        3. Fallback loop batch #2+ — chỉ chạy nếu thiếu entities
        """
        full_text = " ".join(chunks)

        # Bước 1: Fast extract
        final_res = self._fast_extractor.extract(full_text)
        # Normalize spaCy entity names
        for ent in final_res.entities:
            ent.name = self._normalize_name(ent.name)

        # Bước 2: Mandatory LLM Batch #1 — luôn chạy để lấy relations
        first_batch = chunks[:ENTITY_EXTRACTION_BATCH_SIZE]
        try:
            llm_res = await self._extract_llm_batch("\n\n---\n\n".join(first_batch))
            if llm_res:
                final_res = self._merge_results(final_res, llm_res)
        except Exception as e:
            logger = logging.getLogger(__name__)
            logger.error(f"Mandatory LLM batch #1 failed: {e}")

        # Bước 3: Fallback Loop — chỉ chạy nếu thiếu entities
        total_batches = max(1, (len(chunks) + ENTITY_EXTRACTION_BATCH_SIZE - 1) // ENTITY_EXTRACTION_BATCH_SIZE)
        for i in range(1, min(total_batches, ENTITY_EXTRACTION_MAX_LLM_BATCHES)):
            if len(final_res.entities) >= ENTITY_EXTRACTION_MIN_ENTITIES:
                break  # Early exit: đủ entities

            try:
                start = i * ENTITY_EXTRACTION_BATCH_SIZE
                end = start + ENTITY_EXTRACTION_BATCH_SIZE
                batch = chunks[start:end]
                llm_res = await self._extract_llm_batch("\n\n---\n\n".join(batch))
                if llm_res:
                    final_res = self._merge_results(final_res, llm_res)
            except Exception as e:
                logger = logging.getLogger(__name__)
                logger.warning(f"LLM batch #{i+1} failed, skipping: {e}")

        return final_res

    # ============================================================
    # Internal helpers
    # ============================================================

    async def _extract_llm_batch(self, text: str) -> Optional[ExtractionResult]:
        """
        Gọi LLM để trích xuất entities + relations từ 1 đoạn text.
        Dùng lại prompt + schema hiện tại của extract().

        Args:
            text: Combined text của 1 batch

        Returns:
            ExtractionResult hoặc None nếu LLM fail
        """
        prompt = f"""
        Extract key entities and their relationships from the text below.
        Focus on important technical concepts, people, and organizations.
        Output MUST be a JSON object with:
        - "entities": list of objects with "name", "entity_type", "description", "confidence"
        - "relations": list of objects with "source", "target", "relation_type", "description"

        Text:
        {text}
        """
        result = await llm_service.structured_extraction(prompt, ExtractionResult)

        if result:
            # Normalize names
            for entity in result.entities:
                entity.name = self._normalize_name(entity.name)
                # Normalize confidence (0-100 → 0-1)
                if entity.confidence > 1.0:
                    entity.confidence = entity.confidence / 100.0

            # Normalize relation source/target names
            for relation in result.relations:
                relation.source = self._normalize_name(relation.source)
                relation.target = self._normalize_name(relation.target)

        return result

    def _merge_results(self, fast: ExtractionResult, llm: ExtractionResult) -> ExtractionResult:
        """
        Merge strategy:
        1. Index fast entities by lowercase name (key=entity.name.lower())
        2. For each LLM entity:
           - If name matches fast entity → CONFLICT: Keep LLM type & description
           - confidence = max(fast, llm)
           - Mark as "merged"
           - Else → Add LLM entity as-is (entity mới LLM phát hiện)
        3. Add fast entities that had NO LLM match
        4. Merge relations:
           - Dedup by (source, target, relation_type) — ĐÚNG schema
        """
        fast_by_name: dict[str, ExtractedEntity] = {
            e.name.lower(): e for e in fast.entities
        }

        merged_entities: List[ExtractedEntity] = []
        matched_fast_names: set[str] = set()

        # Bước 1: Xử lý LLM entities
        for llm_ent in llm.entities:
            key = llm_ent.name.lower()
            fast_ent = fast_by_name.get(key)

            if fast_ent:
                # CONFLICT: Ưu tiên LLM cho type/description
                merged_entities.append(ExtractedEntity(
                    name=llm_ent.name,
                    entity_type=llm_ent.entity_type,
                    description=llm_ent.description,
                    confidence=max(fast_ent.confidence, llm_ent.confidence)
                ))
                matched_fast_names.add(key)
            else:
                # LLM-only entity
                merged_entities.append(llm_ent)

        # Bước 2: Thêm fast entities không có trong LLM
        for key, fast_ent in fast_by_name.items():
            if key not in matched_fast_names:
                merged_entities.append(fast_ent)

        # Bước 3: Merge relations — dedup bằng (source, target, relation_type)
        merged_relations: List[EntityRelation] = []
        seen_relations: set[tuple[str, str, str]] = set()

        for rel in fast.relations + llm.relations:
            rel_key = (rel.source, rel.target, rel.relation_type)
            if rel_key not in seen_relations:
                merged_relations.append(rel)
                seen_relations.add(rel_key)

        return ExtractionResult(
            entities=merged_entities,
            relations=merged_relations
        )

    # ============================================================
    # Deduplication (giữ nguyên logic cũ)
    # ============================================================

    def deduplicate_entities(self, entities: List[ExtractedEntity]) -> List[ExtractedEntity]:
        """
        Map-Reduce: Merge entities với cùng canonical name.
        Keep longest description and highest confidence.
        """
        from typing import Dict
        merged: Dict[str, ExtractedEntity] = {}
        for entity in entities:
            name = entity.name
            if name not in merged:
                merged[name] = entity
            else:
                if len(entity.description) > len(merged[name].description):
                    merged[name].description = entity.description
                if entity.confidence > merged[name].confidence:
                    merged[name].confidence = entity.confidence

        return list(merged.values())
```

---

### 4. Pipeline Integration (QUAN TRỌNG — V2.4 bổ sung)

#### [MODIFY] `app/core/pipeline.py`

**Thay đổi trong `ingest_text()`** — truyền `raw_chunks` (List[str]) thay vì `combined_text` (str):

```python
# HIỆN TẠI (cũ):
for batch_start in range(0, total_chunks, batch_size):
    batch_chunks = raw_chunks[batch_start:batch_end]
    combined_text = "\n\n---\n\n".join(batch_chunks)
    extraction = await self.extractor.extract(combined_text)  # ← str

# MỚI (V2.4):
# Truyền toàn bộ raw_chunks cho extractor tự quản lý batching
extraction = await self.extractor.extract(raw_chunks)
if extraction:
    all_entities.extend(extraction.entities)
    all_relations.extend(extraction.relations)
```

**Full context — đoạn loop entity extraction trong `ingest_text()` sẽ được thay thế:**

```python
# Trước ( ~20 dòng loop batch ):
for batch_start in range(0, total_chunks, batch_size):
    ...
    extraction = await self.extractor.extract(combined_text)
    ...

# Sau (V2.4 — gọn hơn nhiều):
await self.doc_repo.update_processing_step(doc_id, ProcessingStep.EXTRACTING_ENTITIES)
logger.info(f"Starting entity extraction: {total_chunks} chunks (method={self.extractor._config.ENTITY_EXTRACTION_METHOD if self.extractor._config else 'llm'})")

extraction = await self.extractor.extract(raw_chunks)
if extraction:
    all_entities.extend(extraction.entities)
    all_relations.extend(extraction.relations)

logger.info(f"Entity extraction complete: {len(all_entities)} entities, {len(all_relations)} relations")
```

**Thay đổi trong `__init__` của `LightRAGPipeline`** — không cần thay đổi gì, vì `EntityExtractor` đã nhận `config` qua constructor. Chỉ cần đảm bảo nơi tạo pipeline inject config đúng:

```python
# Nơi tạo EntityExtractor (thường là dependency injection hoặc factory):
from app.config import settings
extractor = EntityExtractor(aliases=None, config=settings)
```

---

### 5. Docker và Requirements

#### [MODIFY] `requirements.txt`
```txt
spacy>=3.7.0
```

#### [MODIFY] `Dockerfile`
```dockerfile
# Sau lệnh RUN pip install -r requirements.txt
RUN pip install spacy && python -m spacy download en_core_web_sm
```

---

## 📊 SO SÁNH TRƯỚC/SAU

| Metric | Trước (LLM only) | Sau (Hybrid V2.4) | Cải thiện |
|--------|-----------------|--------------|-----------|
| **Thời gian (1MB PDF)** | 320s (40 batches × 8s) | ~2s (spaCy) + ~8s (batch 1) + ~40s (fallback ~5 batches) = **~50s** | **~6x nhanh hơn** |
| **RAM Usage** | ~1.2GB (Ollama) | ~50MB (spaCy) + Ollama (chỉ khi fallback) | An toàn hơn |
| **LLM Calls** | 40 calls/document | 1 (mandatory) + ~5 (fallback) = **~6 calls** | **Giảm ~85%** |
| **Entities** | ~50-100 / doc | Tương đương hoặc cao hơn | |
| **Relations** | Có (tất cả batches) | Có (ít nhất từ batch 1) | Đảm bảo chất lượng |
| **Resilience** | LLM fail = không có gì | spaCy luôn có entities | Tốt hơn |

---

## 🗓️ LỘ TRÌNH TRIỂN KHAI

| Bước | Công việc | File(s) | Thời lượng |
|------|----------|---------|-----------|
| **1** | Thêm `spacy` vào requirements.txt & pre-download trong Dockerfile | `requirements.txt`, `Dockerfile` | 10p |
| **2** | Thêm constants + config (`MIN_ENTITIES`, `MAX_LLM_BATCHES`, `METHOD`) | `constants.py`, `config.py`, `.env.example` | 5p |
| **3** | Tạo `fast_extractor.py` (Thread-safe Singleton, Type Mapping) | `fast_extractor.py` | 15p |
| **4** | Sửa `entity_extractor.py` — implement hybrid logic + merge + LLM batch | `entity_extractor.py` | 30p |
| **5** | Sửa `pipeline.py` — truyền `raw_chunks` thay vì loop batch | `pipeline.py` | 10p |
| **6** | Viết unit tests: merge logic, fallback loop, error handling, config switching | `test_fast_extractor.py`, `test_entity_extractor_hybrid.py` | 25p |
| **Tổng** | | | **~95 phút** |

---

## ✅ KẾ HOẠCH XÁC MINH

### Unit Tests (Mới)
```bash
pytest tests/unit/test_fast_extractor.py -v          # Thread-safety, type mapping, extraction
pytest tests/unit/test_entity_extractor_hybrid.py -v  # Merge logic, fallback loop, error handling
```

### Manual Testing Checklist
- [ ] Ingest tài liệu technical ngắn (~5 chunks) → verify luôn có relations từ batch 1
- [ ] Ingest tài liệu dài (~40 chunks) → verify LLM calls ≤ 10 (max batches)
- [ ] Test `ENTITY_EXTRACTION_METHOD=llm` → pipeline hoạt động như cũ (backward compat)
- [ ] Test `ENTITY_EXTRACTION_METHOD=spacy_only` → không gọi LLM, chỉ spaCy
- [ ] Test `ENTITY_EXTRACTION_METHOD=hybrid` → fallback trigger khi <30 entities, early exit khi đủ
- [ ] Test LLM failure: mock LLM raise exception → vẫn có spaCy entities, relations = rỗng
- [ ] `docker stats` → RAM toàn container duy trì dưới 1.5GB
- [ ] Thử xoá spaCy model → verify fail-fast với RuntimeError rõ ràng

---

## 🚨 RỦI RO & GIẢM THIỂU

| Rủi ro | Khả năng | Impact | Giảm thiểu |
|--------|---------|--------|-----------|
| **spaCy model missing** | Thấp | Cao | Fail-fast với RuntimeError + log rõ ràng |
| **LLM batch fail liên tiếp** | Trung bình | Trung bình | try/except từng batch, vẫn có spaCy entities |
| **Relations ít/không có** | Trung bình | Thấp | Mandatory batch #1 đảm bảo luôn có ít nhất 1 batch relations |
| **OOM trên worker** | Thấp | Thấp | spaCy ~50MB, singleton shared, hoàn toàn kiểm soát được |
| **Type mismatch spaCy→hệ thống** | Đã fix | — | `SPACY_TO_STANDARD_TYPES` mapping đầy đủ |

---

## 📌 KẾT LUẬN

**Đánh giá V2.4**: ✅ **SẴN SÀNG TRIỂN KHAI**

Kế hoạch đã hoàn thiện ở mức **95%+, giải quyết triệt để**:
- ✅ Thread-safe Singleton với `threading.Lock()`
- ✅ Type mapping spaCy → hệ thống (`SPACY_TO_STANDARD_TYPES`)
- ✅ Merge algorithm chi tiết với `rel.source`/`rel.target` (đúng schema)
- ✅ Fallback loop với `ENTITY_EXTRACTION_BATCH_SIZE` constant (không hardcode)
- ✅ Error handling: try/except từng batch, không crash toàn bộ
- ✅ Relations safety: mandatory batch #1 luôn chạy
- ✅ Pipeline integration rõ ràng: truyền `List[str]` thay vì `str`
- ✅ Backward compatibility: 3 modes (`llm`, `hybrid`, `spacy_only`)
- ✅ Config placement đúng: constants trong `constants.py`, method toggle trong `config.py`
- ✅ Model name đúng: `hf.co/Qwen/Qwen2.5-1.5B-Instruct-GGUF:Q4_K_M`

**Còn ~5% rủi ro chấp nhận được:**
- spaCy không trích xuất relations — phó thác cho LLM mandatory batch (đã giảm thiểu)
- Threshold `30` có thể cần tune lại sau khi test với documents thật
- Entity types từ spaCy có thể ít chi tiết hơn LLM (đã giải quyết bằng merge strategy ưu tiên LLM)

**Next Step:** Tiến hành Implementation Phase — Bắt đầu với Step 1 (requirements + Dockerfile).
