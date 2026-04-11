import os
import uuid
from pathlib import Path
from typing import Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from ..core.markdown_parser import MarkdownParser
from ..repositories.graph_repo import GraphRepository
from ..services.entity_resolution_service import EntityResolutionService
from ..core.graph_builder import get_graph_builder
import logging

logger = logging.getLogger(__name__)

class ObsidianVaultImporter:
    """
    Service to import notes from an Obsidian Vault into the Knowledge Graph.
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = GraphRepository(db)
        self.parser = MarkdownParser()
        self.resolution_service = EntityResolutionService(db)
        self.graph_builder = get_graph_builder()

    async def import_vault(self, vault_path: str, user_id: uuid.UUID, import_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Scan vault_path and import all .md files as entities and wiki-links as relations.
        """
        from ..worker.queue import get_redis_pool
        redis = await get_redis_pool() if import_id else None
        progress_key = f"import:{import_id}:progress" if import_id else None

        root = Path(vault_path)
        if not root.exists() or not root.is_dir():
            raise ValueError(f"Vault path does not exist or is not a directory: {vault_path}")

        parsed_notes = []
        files_found = []
        
        # 1. Scan
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if not d.startswith('.')]
            for filename in filenames:
                if filename.endswith('.md'):
                    files_found.append(Path(dirpath) / filename)

        if not files_found:
            return {"entities_imported": 0, "relations_imported": 0, "message": "No markdown files found."}

        # 2. Parse
        total_files = len(files_found)
        for i, file_path in enumerate(files_found):
            try:
                note = self.parser.parse_file(file_path)
                parsed_notes.append(note)
                
                if redis and progress_key:
                    progress = int(((i + 1) / total_files) * 30) # 0-30% for parsing
                    await redis.setex(progress_key, 3600, f"Parsing notes: {i+1}/{total_files} ({progress}%)")
            except Exception as e:
                logger.error(f"Error parsing {file_path}: {e}")

        # 3. Upsert Entities
        import_stats = {
            "entities_imported": 0,
            "relations_imported": 0,
            "errors": []
        }
        # Dual mapping: filename (primary, matches Obsidian behavior) + title (fallback)
        filename_to_id = {}
        title_to_id = {}

        for i, note in enumerate(parsed_notes):
            try:
                entity_data = {
                    "canonical_name": note.title,
                    "entity_type": "note",
                    "description": note.content[:500] + ("..." if len(note.content) > 500 else ""),
                    "confidence": 1.0,
                    "source": "obsidian_import",
                    "tags": note.tags,
                    "file_path": str(note.file_path),
                    "metadata": note.frontmatter
                }

                entity = await self.resolution_service.resolve_and_merge(user_id, entity_data)
                # Map both filename (primary) and title (fallback) to entity ID
                filename_to_id[note.filename.lower()] = entity.id
                title_to_id[note.title.lower()] = entity.id
                import_stats["entities_imported"] += 1

                if redis and progress_key:
                    progress = 30 + int(((i + 1) / len(parsed_notes)) * 40) # 30-70% for entities
                    await redis.setex(progress_key, 3600, f"Importing entities: {i+1}/{len(parsed_notes)} ({progress}%)")
            except Exception as e:
                import_stats["errors"].append(f"Entity error ({note.title}): {e}")
                logger.error(f"Entity error ({note.title}): {e}", exc_info=True)

        # 4. Create Relations
        for i, note in enumerate(parsed_notes):
            # Resolve source entity (by filename first, then title)
            source_id = filename_to_id.get(note.filename.lower()) or title_to_id.get(note.title.lower())
            if not source_id:
                logger.warning(f"Could not resolve source entity for: {note.filename} ({note.title})")
                continue

            for link_target in note.links:
                # Resolve target entity: try filename first (Obsidian behavior), then title
                link_lower = link_target.lower()
                target_id = filename_to_id.get(link_lower) or title_to_id.get(link_lower)
                
                if target_id:
                    try:
                        # Use bulk_upsert_relations với document_id placeholder
                        from uuid import NAMESPACE_DNS
                        relations = [{
                            "source_entity_id": source_id,
                            "target_entity_id": target_id,
                            "relation_type": "links_to",
                            "description": f"Wiki-link from [[{note.title}]] to [[{link_target}]]",
                            "source": "obsidian_import",
                            "is_backlink": False,
                            "document_id": NAMESPACE_DNS
                        }]
                        await self.repo.bulk_upsert_relations(relations, NAMESPACE_DNS)
                        import_stats["relations_imported"] += 1
                    except Exception as e:
                        logger.warning(f"Error creating relation from {note.title} to {link_target}: {e}")
                else:
                    logger.debug(f"Could not resolve link target: {link_target}")
            
            if redis and progress_key:
                progress = 70 + int(((i + 1) / len(parsed_notes)) * 20) # 70-90% for relations
                await redis.setex(progress_key, 3600, f"Building relations: {i+1}/{len(parsed_notes)} ({progress}%)")

        # 4. Update GraphBuilder and Persist
        try:
            # Prepare entities and relations for GraphBuilder
            builder_entities = []
            for note in parsed_notes:
                builder_entities.append({
                    "canonical_name": note.title,
                    "entity_type": "note",
                    "description": note.content[:500]
                })
            
            # Since relations in GraphBuilder expect canonical names
            builder_relations = []
            for note in parsed_notes:
                for link_target in note.links:
                    builder_relations.append({
                        "source_entity": note.title,
                        "target_entity": link_target,
                        "relation_type": "links_to",
                        "description": f"Wiki-link from [[{note.title}]] to [[{link_target}]]"
                    })
            
            await self.graph_builder.add_entities_and_relations(builder_entities, builder_relations, document_id="obsidian_global")
            await self.graph_builder.persist_graph("obsidian_global")
            if redis and progress_key:
                await redis.setex(progress_key, 3600, "Import completed: 100%")
        except Exception as e:
            logger.error(f"Error updating GraphBuilder for obsidian: {e}")

        await self.db.commit()
        return import_stats
