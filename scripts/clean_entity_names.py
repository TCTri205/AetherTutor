#!/usr/bin/env python3
"""
Data Cleaning Script: Clean Entity Names for Migration 6

Mục đích: Trước khi migration graph_relations từ String -> UUID FK,
cần đảm bảo tất cả source_entity và target entity names khớp chính xác
với graph_entities.canonical_name.

Cách hoạt động:
1. Quét toàn bộ graph_relations, thu thập tất cả entity names unique
2. Fuzzy match từng entity name với graph_entities.canonical_name (threshold 0.85)
3. Với mỗi match -> gán vào canonical_name tương ứng
4. Với mỗi unresolved entity (không match được) -> log ra file unresolved_entities.csv
5. Báo cáo tổng quan

Usage:
    python scripts/clean_entity_names.py [--threshold 0.85] [--dry-run] [--output unresolved_entities.csv]
"""

import argparse
import csv
import difflib
import logging
import sys
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import asyncio
from sqlalchemy import select, update, text
from sqlalchemy.ext.asyncio import AsyncSession

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database import AsyncSessionLocal
from app.models.graph import GraphEntity, GraphRelation

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("logs/clean_entity_names.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)


async def get_all_canonical_names(db: AsyncSession) -> List[str]:
    """Lấy tất cả canonical_name từ graph_entities table."""
    result = await db.execute(
        select(GraphEntity.canonical_name).distinct()
    )
    return [row[0] for row in result.fetchall()]


async def get_all_entity_names_from_relations(
    db: AsyncSession,
) -> Dict[str, List[Tuple[str, str]]]:
    """
    Lấy tất cả source_entity và target_entity từ graph_relations.
    Returns: Dict mapping entity_name -> list of (relation_id, relation_type)
    """
    result = await db.execute(
        select(
            GraphRelation.id,
            GraphRelation.source_entity,
            GraphRelation.target_entity,
            GraphRelation.relation_type,
        )
    )
    
    entity_occurrences = defaultdict(list)
    
    for row in result.fetchall():
        rel_id, source, target, rel_type = row
        entity_occurrences[source].append((str(rel_id), rel_type))
        if source != target:  # Tránh duplicate nếu source == target
            entity_occurrences[target].append((str(rel_id), rel_type))
    
    return dict(entity_occurrences)


def fuzzy_match_entity_name(
    entity_name: str,
    canonical_names: List[str],
    threshold: float = 0.85,
) -> Optional[Tuple[str, float]]:
    """
    Fuzzy match entity name với danh sách canonical names.
    
    Returns:
        (matched_canonical_name, similarity_score) hoặc None nếu không match
    """
    if not canonical_names:
        return None
    
    # Dùng SequenceMatcher để tính similarity
    best_match = None
    best_score = 0.0
    
    for canonical in canonical_names:
        # Exact match优先
        if entity_name.lower() == canonical.lower():
            return (canonical, 1.0)
        
        score = difflib.SequenceMatcher(
            None, entity_name.lower(), canonical.lower()
        ).ratio()
        
        if score > best_score:
            best_score = score
            best_match = canonical
    
    if best_score >= threshold:
        return (best_match, best_score)
    
    return None


async def resolve_entity_names(
    db: AsyncSession,
    threshold: float = 0.85,
    dry_run: bool = False,
) -> Dict:
    """
    Main resolution logic: fuzzy match và update entity names trong relations.
    
    Returns:
        Statistics dict với resolved/unresolved counts
    """
    logger.info("=== BẮT ĐẦU DATA CLEANING: ENTITY NAME RESOLUTION ===")
    
    # Bước 1: Lấy canonical names
    logger.info("Bước 1: Lấy canonical names từ graph_entities...")
    canonical_names = await get_all_canonical_names(db)
    logger.info(f"  Tìm thấy {len(canonical_names)} canonical names")
    
    if not canonical_names:
        logger.warning("⚠️ Không có entity nào trong graph_entities! Dừng script.")
        return {"error": "No entities found"}
    
    # Bước 2: Lấy tất cả entity names từ relations
    logger.info("Bước 2: Quét graph_relations để thu thập entity names...")
    entity_occurrences = await get_all_entity_names_from_relations(db)
    unique_entity_names = list(entity_occurrences.keys())
    logger.info(f"  Tìm thấy {len(unique_entity_names)} entity names unique")
    
    # Bước 3: Fuzzy match từng entity name
    logger.info("Bước 3: Fuzzy matching với threshold %.2f...", threshold)
    
    resolved_mapping: Dict[str, str] = {}
    unresolved_entities: Dict[str, dict] = {}
    
    for entity_name in unique_entity_names:
        match_result = fuzzy_match_entity_name(entity_name, canonical_names, threshold)
        
        if match_result:
            canonical_name, score = match_result
            resolved_mapping[entity_name] = canonical_name
        else:
            # Unresolved - log để manual review
            occurrences = entity_occurrences[entity_name]
            unresolved_entities[entity_name] = {
                "occurrence_count": len(occurrences),
                "sample_relations": occurrences[:5],  # Chỉ lấy 5 samples
            }
    
    # Thống kê
    total_relations = len(entity_occurrences)
    resolved_count = len(resolved_mapping)
    unresolved_count = len(unresolved_entities)
    total_unique = resolved_count + unresolved_count
    
    logger.info(f"\n{'='*60}")
    logger.info(f"KẾT QUẢ RESOLUTION:")
    logger.info(f"  Total unique entity names: {total_unique}")
    logger.info(f"  ✅ Resolved: {resolved_count} ({resolved_count/total_unique*100:.1f}%)")
    logger.info(f"  ❌ Unresolved: {unresolved_count} ({unresolved_count/total_unique*100:.1f}%)")
    logger.info(f"{'='*60}\n")
    
    # Bước 4: Nếu dry-run, không update DB
    if dry_run:
        logger.info("[DRY RUN] Không thực hiện update. Chỉ hiển thị kết quả.")
        
        if resolved_mapping:
            logger.info("\nSample resolved mappings (first 20):")
            for i, (original, canonical) in enumerate(list(resolved_mapping.items())[:20]):
                logger.info(f"  {i+1}. '{original}' -> '{canonical}'")
        
        if unresolved_entities:
            logger.info(f"\nUnresolved entities ({unresolved_count}):")
            for entity_name, info in list(unresolved_entities.items())[:20]:
                logger.info(
                    f"  - '{entity_name}' (occurrences: {info['occurrence_count']})"
                )
        
        return {
            "resolved_count": resolved_count,
            "unresolved_count": unresolved_count,
            "total_unique": total_unique,
            "resolved_mapping": resolved_mapping,
            "unresolved_entities": unresolved_entities,
            "dry_run": True,
        }
    
    # Bước 5: Update graph_relations với resolved names
    if resolved_mapping:
        logger.info("Bước 5: Update graph_relations với resolved names...")
        
        updated_count = 0
        for original_name, canonical_name in resolved_mapping.items():
            if original_name == canonical_name:
                continue  # Skip nếu đã trùng
            
            # Update source_entity
            await db.execute(
                text("""
                    UPDATE graph_relations
                    SET source_entity = :canonical
                    WHERE source_entity = :original
                """),
                {"canonical": canonical_name, "original": original_name},
            )
            
            # Update target_entity
            await db.execute(
                text("""
                    UPDATE graph_relations
                    SET target_entity = :canonical
                    WHERE target_entity = :original
                """),
                {"canonical": canonical_name, "original": original_name},
            )
            
            updated_count += 1
        
        await db.commit()
        logger.info(f"  ✅ Đã update {updated_count} entity names")
    
    # Bước 6: Export unresolved entities ra CSV
    output_file = Path("logs/unresolved_entities.csv")
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    if unresolved_entities:
        logger.warning(f"\n⚠️ CÓ {unresolved_count} UNRESOLVED ENTITIES!")
        logger.warning(f"  Export ra file: {output_file}")
        
        with open(output_file, "w", newline="", encoding="utf-8") as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow([
                "entity_name",
                "occurrence_count",
                "sample_relations",
                "action_required",
            ])
            
            for entity_name, info in unresolved_entities.items():
                sample_rels = "; ".join(
                    f"{rel_id}:{rel_type}"
                    for rel_id, rel_type in info["sample_relations"]
                )
                writer.writerow([
                    entity_name,
                    info["occurrence_count"],
                    sample_rels,
                    "MANUAL_REVIEW_REQUIRED",
                ])
        
        logger.warning("  File CSV đã được tạo. Hãy review và quyết định:")
        logger.warning("    - Gán thủ công vào canonical name đúng")
        logger.warning("    - Hoặc đánh dấu DELETE nếu entity không còn tồn tại")
    
    # Bước 7: Kiểm tra xem có > 5% unresolved không
    unresolved_percentage = (
        (unresolved_count / total_unique * 100) if total_unique > 0 else 0
    )
    
    if unresolved_percentage > 5.0:
        logger.error(f"\n🛑 DỪNG MIGRATION! Unresolved entities > 5% ({unresolved_percentage:.1f}%)")
        logger.error("  Hãy manual review toàn bộ unresolved entities trước khi tiếp tục.")
        return {
            "resolved_count": resolved_count,
            "unresolved_count": unresolved_count,
            "total_unique": total_unique,
            "unresolved_percentage": unresolved_percentage,
            "resolved_mapping": resolved_mapping,
            "unresolved_entities": unresolved_entities,
            "blocked": True,
        }
    
    logger.info(f"\n✅ DATA CLEANING HOÀN TẤT!")
    logger.info(f"  Resolved: {resolved_count}/{total_unique}")
    logger.info(f"  Unresolved: {unresolved_count}/{total_unique} ({unresolved_percentage:.1f}%)")
    logger.info(f"  Sẵn sàng cho Migration 6 (String -> UUID FK)")
    
    return {
        "resolved_count": resolved_count,
        "unresolved_count": unresolved_count,
        "total_unique": total_unique,
        "unresolved_percentage": unresolved_percentage,
        "resolved_mapping": resolved_mapping,
        "unresolved_entities": unresolved_entities,
        "blocked": False,
    }


async def main():
    parser = argparse.ArgumentParser(
        description="Clean entity names before Migration 6"
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.85,
        help="Fuzzy match threshold (default: 0.85)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Chỉ hiển thị kết quả, không update DB",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="logs/unresolved_entities.csv",
        help="Output file cho unresolved entities",
    )
    
    args = parser.parse_args()
    
    async with AsyncSessionLocal() as db:
        try:
            result = await resolve_entity_names(
                db, threshold=args.threshold, dry_run=args.dry_run
            )
            
            if result.get("error"):
                logger.error(f"Lỗi: {result['error']}")
                sys.exit(1)
            
            if result.get("blocked"):
                logger.error("\n❌ DATA CLEANING BLOCKED!")
                logger.error("  Hãy review unresolved entities và chạy lại script.")
                sys.exit(2)
            
            logger.info("\nScript hoàn tất thành công!")
            
        except Exception as e:
            logger.error(f"Lỗi khi chạy script: {e}", exc_info=True)
            await db.rollback()
            sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
