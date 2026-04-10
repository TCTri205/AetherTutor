"""
Entity Extractor — Hybrid (spaCy + LLM fallback)
Kết hợp trích xuất nhanh bằng spaCy và trích xuất sâu bằng LLM.
"""
import logging
from typing import List, Optional, Dict
from ..schemas.lightrag import ExtractionResult, ExtractedEntity, EntityRelation
from ..services.llm_service import llm_service
from ..constants import (
    ENTITY_EXTRACTION_BATCH_SIZE,
    ENTITY_EXTRACTION_MIN_ENTITIES,
    ENTITY_EXTRACTION_MAX_LLM_BATCHES,
)

logger = logging.getLogger(__name__)

class EntityExtractor:
    """
    Hybrid entity extractor:
    - Fast layer: spaCy (trích xuất nhanh toàn bộ thực thể)
    - Fallback layer: LLM (trích xuất quan hệ và thực thể bổ sung theo từng batch)
    """

    def __init__(self, aliases: dict = None, config=None):
        self.aliases = aliases or {}
        self._config = config

        # Lazy-init FastExtractor chỉ khi phương thức là hybrid hoặc spacy_only
        method = getattr(config, "ENTITY_EXTRACTION_METHOD", "llm") if config else "llm"
        if method in ("hybrid", "spacy_only"):
            try:
                from .fast_extractor import FastExtractor
                self._fast_extractor = FastExtractor()
            except Exception as e:
                logger.error(f"Failed to initialize FastExtractor: {e}")
                self._fast_extractor = None
        else:
            self._fast_extractor = None

    def _normalize_name(self, name: str) -> str:
        clean_name = name.strip().lower()
        if clean_name in self.aliases:
            return self.aliases[clean_name]
        return name.strip().title()

    # ============================================================
    # Public API — Nhận List[str] để tự quản lý batching
    # ============================================================

    async def extract(self, chunks: List[str]) -> Optional[ExtractionResult]:
        """
        Trích xuất thực thể & quan hệ từ danh sách các đoạn văn bản.

        Args:
            chunks: Danh sách các đoạn văn bản (đã được chia bởi pipeline).

        Returns:
            ExtractionResult chứa danh sách thực thể và quan hệ.
        """
        method = getattr(self._config, "ENTITY_EXTRACTION_METHOD", "llm") if self._config else "llm"

        if method == "spacy_only":
            return await self._extract_spacy_only(chunks)
        elif method == "hybrid":
            return await self._extract_hybrid(chunks)
        else:  # "llm" — giữ nguyên logic cũ (cho tất cả các batch)
            return await self._extract_llm_legacy(chunks)

    # ============================================================
    # Phương thức trích xuất LLM cũ (Lặp qua tất cả các batch)
    # ============================================================

    async def _extract_llm_legacy(self, chunks: List[str]) -> Optional[ExtractionResult]:
        """Gộp logic loop cũ của pipeline vào đây để đảm bảo tính nhất quán của API."""
        all_entities = []
        all_relations = []
        total_chunks = len(chunks)
        batch_size = ENTITY_EXTRACTION_BATCH_SIZE
        
        total_batches = (total_chunks + batch_size - 1) // batch_size
        logger.info(f"Using Legacy LLM Extraction: {total_chunks} chunks, {total_batches} batches")

        for i in range(total_batches):
            batch = chunks[i * batch_size : (i + 1) * batch_size]
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
        """Chỉ dùng spaCy, không gọi LLM."""
        if not self._fast_extractor:
            logger.error("FastExtractor not initialized but spacy_only method requested")
            return None

        full_text = " ".join(chunks)
        result = self._fast_extractor.extract(full_text)
        
        # Normalize names
        for ent in result.entities:
            ent.name = self._normalize_name(ent.name)
        return result

    # ============================================================
    # Hybrid mode (SpaCy + LLM Fallback)
    # ============================================================

    async def _extract_hybrid(self, chunks: List[str]) -> Optional[ExtractionResult]:
        """
        Quy trình Hybrid:
        1. Dùng spaCy quét toàn bộ văn bản để lấy các thực thể cơ bản.
        2. Chạy 1 batch LLM đầu tiên (Mandatory) để đảm bảo có quan hệ (Relations).
        3. Nếu số lượng thực thể chưa đạt ngưỡng (MIN_ENTITIES), tiếp tục gọi LLM cho các batch tiếp theo.
        """
        if not self._fast_extractor:
            logger.warning("FastExtractor not available, falling back to Legacy LLM")
            return await self._extract_llm_legacy(chunks)

        full_text = " ".join(chunks)

        # Bước 1: Trích xuất nhanh bằng spaCy
        final_res = self._fast_extractor.extract(full_text)
        for ent in final_res.entities:
            ent.name = self._normalize_name(ent.name)

        # Bước 2: Luôn chạy Batch LLM #1 để lấy quan hệ (chất lượng cao)
        first_batch = chunks[:ENTITY_EXTRACTION_BATCH_SIZE]
        try:
            llm_res = await self._extract_llm_batch("\n\n---\n\n".join(first_batch))
            if llm_res:
                final_res = self._merge_results(final_res, llm_res)
        except Exception as e:
            logger.error(f"Mandatory LLM batch #1 failed: {e}")

        # Bước 3: Vòng lặp Fallback cho các batch tiếp theo
        total_chunks = len(chunks)
        batch_size = ENTITY_EXTRACTION_BATCH_SIZE
        total_batches = (total_chunks + batch_size - 1) // batch_size

        for i in range(1, min(total_batches, ENTITY_EXTRACTION_MAX_LLM_BATCHES)):
            # Kiểm tra ngưỡng dừng
            if len(final_res.entities) >= ENTITY_EXTRACTION_MIN_ENTITIES:
                logger.info(f"Hybrid extraction early exit at batch {i+1}: {len(final_res.entities)} entities found")
                break

            try:
                start = i * batch_size
                end = start + batch_size
                batch = chunks[start:end]
                llm_res = await self._extract_llm_batch("\n\n---\n\n".join(batch))
                if llm_res:
                    final_res = self._merge_results(final_res, llm_res)
            except Exception as e:
                logger.warning(f"LLM batch #{i+1} failed, skipping: {e}")

        return final_res

    # ============================================================
    # Internal Helpers
    # ============================================================

    async def _extract_llm_batch(self, text: str) -> Optional[ExtractionResult]:
        """Gọi LLM để trích xuất thực thể và quan hệ từ một khối văn bản."""
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
            # Normalize names and confidence
            for entity in result.entities:
                entity.name = self._normalize_name(entity.name)
                if entity.confidence > 1.0:
                    entity.confidence = entity.confidence / 100.0

            for relation in result.relations:
                relation.source = self._normalize_name(relation.source)
                relation.target = self._normalize_name(relation.target)

        return result

    def _merge_results(self, fast: ExtractionResult, llm: ExtractionResult) -> ExtractionResult:
        """
        Thuật toán gộp kết quả:
        1. Ưu tiên thực thể từ LLM (về mô tả và loại thực thể).
        2. Kết hợp thực thể từ spaCy nếu không có trong LLM.
        3. Gộp toàn bộ quan hệ (loại bỏ trùng lặp).
        """
        fast_by_name: Dict[str, ExtractedEntity] = {
            e.name.lower(): e for e in fast.entities
        }

        merged_entities: List[ExtractedEntity] = []
        matched_fast_names: set[str] = set()

        # Step 1: Xử lý thực thể từ LLM
        for llm_ent in llm.entities:
            key = llm_ent.name.lower()
            fast_ent = fast_by_name.get(key)

            if fast_ent:
                # Xung đột: Ưu tiên LLM cho description và type, lấy tự tin cao nhất
                merged_entities.append(ExtractedEntity(
                    name=llm_ent.name,
                    entity_type=llm_ent.entity_type,
                    description=llm_ent.description,
                    confidence=max(fast_ent.confidence, llm_ent.confidence)
                ))
                matched_fast_names.add(key)
            else:
                # Thực thể chỉ có ở LLM
                merged_entities.append(llm_ent)

        # Step 2: Thêm thực thể spaCy không bị trùng
        for key, fast_ent in fast_by_name.items():
            if key not in matched_fast_names:
                merged_entities.append(fast_ent)

        # Step 3: Gộp quan hệ và loại bỏ trùng lặp theo (source, target, type)
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

    def deduplicate_entities(self, entities: List[ExtractedEntity]) -> List[ExtractedEntity]:
        """
        Gộp các thực thể có cùng tên chuẩn hóa.
        Giữ lại mô tả dài nhất và độ tự tin cao nhất.
        """
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
