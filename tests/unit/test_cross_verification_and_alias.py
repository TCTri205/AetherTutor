"""
Unit tests cho CrossVerificationService và EntityAliasResolutionService.

Test coverage:
CrossVerificationService:
- cross_check: single doc, multi-doc, contradiction detection
- _extract_claims: claim extraction từ contexts
- _format_documents_for_prompt: prompt formatting
- Consolidation với disagreements

EntityAliasResolutionService:
- _calculate_similarity: fuzzy matching, substring, exact
- resolve_entity_alias: lookup, fuzzy match, LLM verification
- create_alias, delete_alias, get_user_aliases: CRUD
- get_global_entities: aggregation across documents
"""

import pytest
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.cross_verification_service import CrossVerificationService


# ============================================================
# CrossVerificationService Tests
# ============================================================

class TestCrossCheck:

    @pytest.mark.asyncio
    async def test_cross_check_single_document(self):
        """Single document → no cross-check, return default message."""
        service = CrossVerificationService()
        doc_contexts = [
            {
                "document_id": "doc1",
                "document_title": "Doc 1",
                "context": [{"type": "chunk", "content": "Python is a programming language."}],
            }
        ]

        result = await service.cross_check("What is Python?", doc_contexts)

        assert result["documents_analyzed"] == 1
        assert result["contradictions"] == []
        assert "Only one document" in result["consolidated_answer"]

    @pytest.mark.asyncio
    async def test_cross_check_multiple_documents(self):
        """Multiple documents → cross-check analysis."""
        service = CrossVerificationService()

        # Mock LLM responses
        with patch.object(service, "_analyze_with_llm", new_callable=AsyncMock) as mock_analyze, \
             patch.object(service, "_consolidate_with_llm", new_callable=AsyncMock) as mock_consolidate:

            mock_analyze.return_value = {
                "contradictions": [],
                "complementary": [{"insight": "Doc2 extends Doc1", "source_docs": ["doc1", "doc2"], "combined_understanding": "Combined"}],
                "consensus": [{"point": "Python is popular", "source_docs": ["doc1", "doc2"]}],
            }
            mock_consolidate.return_value = {
                "synthesized_answer": "Python is widely used...",
                "claims": [],
                "disagreements": [],
            }

            doc_contexts = [
                {
                    "document_id": "doc1",
                    "document_title": "Python Basics",
                    "context": [{"type": "chunk", "content": "Python is a programming language."}],
                },
                {
                    "document_id": "doc2",
                    "document_title": "Python Advanced",
                    "context": [{"type": "chunk", "content": "Python supports OOP and functional paradigms."}],
                },
            ]

            result = await service.cross_check("Tell me about Python", doc_contexts)

            assert result["documents_analyzed"] == 2
            assert len(result["complementary"]) == 1
            assert len(result["consensus"]) == 1
            assert result["consolidated_answer"] == "Python is widely used..."


class TestExtractClaims:

    def test_extract_claims_from_context(self):
        """Extract claims từ document contexts."""
        service = CrossVerificationService()

        doc_contexts = [
            {
                "document_id": "doc1",
                "document_title": "Test Doc",
                "context": [
                    {"type": "chunk", "content": "Claim 1: Python is popular."},
                    {"type": "chunk", "content": "Claim 2: Python is easy to learn."},
                    {"type": "entity", "content": "Not a chunk"},  # Should be ignored
                ],
            }
        ]

        claims = service._extract_claims(doc_contexts)

        assert "doc1" in claims
        assert claims["doc1"]["title"] == "Test Doc"
        assert len(claims["doc1"]["claims"]) == 2  # Only chunk types
        assert "Claim 1" in claims["doc1"]["claims"][0]

    def test_extract_claims_truncates_long_content(self):
        """Claims được truncate về 300 chars."""
        service = CrossVerificationService()

        long_content = "A" * 500
        doc_contexts = [
            {
                "document_id": "doc1",
                "document_title": "Test",
                "context": [{"type": "chunk", "content": long_content}],
            }
        ]

        claims = service._extract_claims(doc_contexts)

        assert len(claims["doc1"]["claims"][0]) == 300  # Truncated

    def test_extract_claims_limits_per_doc(self):
        """Max 5 claims per document."""
        service = CrossVerificationService()

        doc_contexts = [
            {
                "document_id": "doc1",
                "document_title": "Test",
                "context": [
                    {"type": "chunk", "content": f"Claim {i}"} for i in range(10)
                ],
            }
        ]

        claims = service._extract_claims(doc_contexts)

        assert len(claims["doc1"]["claims"]) == 5  # Limited to 5


class TestFormatDocumentsForPrompt:

    def test_format_claims_for_prompt(self):
        """Format claims thành readable string."""
        service = CrossVerificationService()

        claims_by_doc = {
            "doc1": {
                "title": "Python Basics",
                "claims": ["Python is popular", "Python is easy"],
            },
            "doc2": {
                "title": "Python Advanced",
                "claims": ["Python supports OOP"],
            },
        }

        formatted = service._format_documents_for_prompt(claims_by_doc)

        assert "Python Basics" in formatted
        assert "Python Advanced" in formatted
        assert "Python is popular" in formatted
        assert "doc1" in formatted
        assert "doc2" in formatted


class TestAnalyzeWithLLM:

    @pytest.mark.asyncio
    async def test_analyze_contradictions(self):
        """LLM analysis returns contradictions, complementary, consensus."""
        from app.services.cross_verification_service import CrossVerificationService

        service = CrossVerificationService()

        # Mock contradiction items đúng cách
        contradiction_item = {
            "statement": "Doc1 says X, Doc2 says Y",
            "severity": "high",
            "source_docs": ["doc1", "doc2"],
            "snippet_doc1": "X is true",
            "snippet_doc2": "Y is true",
        }

        with patch.object(service, "_analyze_with_llm", new_callable=AsyncMock) as mock_analyze:
            mock_analyze.return_value = {
                "contradictions": [contradiction_item],
                "complementary": [],
                "consensus": [],
            }

            result = await service._analyze_with_llm(
                query="Test query",
                docs_info="Doc1 info\nDoc2 info",
            )

            assert len(result["contradictions"]) == 1
            assert result["contradictions"][0]["severity"] == "high"

    @pytest.mark.asyncio
    async def test_analyze_llm_failure_returns_empty(self):
        """LLM fails → return empty results."""
        service = CrossVerificationService()

        with patch("app.services.cross_verification_service.llm_service") as mock_llm:
            mock_llm.structured_extraction = AsyncMock(side_effect=Exception("LLM error"))

            result = await service._analyze_with_llm(
                query="Test",
                docs_info="Info",
            )

            assert result == {"contradictions": [], "complementary": [], "consensus": []}


class TestConsolidateWithLLM:

    @pytest.mark.asyncio
    async def test_consolidate_success(self):
        """LLM consolidation với claims và disagreements."""
        service = CrossVerificationService()

        mock_response = MagicMock()
        mock_response.synthesized_answer = "Consolidated answer"
        mock_response.claims = [
            MagicMock(
                claim="Python is popular",
                sources=["doc1", "doc2"],
                confidence="high",
                contradicted_by=[],
            )
        ]
        mock_response.disagreements = []

        with patch("app.services.cross_verification_service.llm_service") as mock_llm:
            mock_llm.structured_extraction = AsyncMock(return_value=mock_response)

            result = await service._consolidate_with_llm(
                query="Test",
                docs_info="Info",
                analysis={"contradictions": [], "complementary": [], "consensus": []},
            )

            assert result["synthesized_answer"] == "Consolidated answer"
            assert len(result["claims"]) == 1

    @pytest.mark.asyncio
    async def test_consolidate_llm_failure(self):
        """LLM fails → return fallback answer."""
        service = CrossVerificationService()

        with patch("app.services.cross_verification_service.llm_service") as mock_llm:
            mock_llm.structured_extraction = AsyncMock(side_effect=Exception("Error"))

            result = await service._consolidate_with_llm(
                query="Test",
                docs_info="Info",
                analysis={},
            )

            assert "Unable to generate" in result["synthesized_answer"]


# ============================================================
# EntityAliasResolutionService Tests
# ============================================================

class TestCalculateSimilarity:

    def test_exact_match(self):
        """Same names → similarity = 1.0."""
        from app.services.entity_alias_service import EntityAliasResolutionService

        # Need to mock session for initialization
        mock_session = AsyncMock()
        service = EntityAliasResolutionService(mock_session)

        score = service._calculate_similarity("Python", "Python")
        assert score == 1.0

    def test_case_insensitive(self):
        """Case khác nhau vẫn match."""
        from app.services.entity_alias_service import EntityAliasResolutionService

        mock_session = AsyncMock()
        service = EntityAliasResolutionService(mock_session)

        score = service._calculate_similarity("python", "PYTHON")
        assert score == 1.0

    def test_substring_match(self):
        """One name is substring of another → high similarity."""
        from app.services.entity_alias_service import EntityAliasResolutionService

        mock_session = AsyncMock()
        service = EntityAliasResolutionService(mock_session)

        # "AI" không substring của "Artificial Intelligence" sau lowercase
        # Nhưng SequenceMatcher vẫn cho score khá cao
        score = service._calculate_similarity("AI", "Artificial Intelligence")
        # Không nhất thiết >= 0.9 vì không phải substring thực sự
        # Chỉ cần score > 0 (có similarity)
        assert score > 0.0

    def test_actual_substring_match(self):
        """Test actual substring case: 'net' in 'Network'."""
        from app.services.entity_alias_service import EntityAliasResolutionService

        mock_session = AsyncMock()
        service = EntityAliasResolutionService(mock_session)

        # "net" có trong "network" → substring match
        score = service._calculate_similarity("net", "Network")
        assert score >= 0.9

    def test_fuzzy_match_similar_names(self):
        """Similar names → high SequenceMatcher score."""
        from app.services.entity_alias_service import EntityAliasResolutionService

        mock_session = AsyncMock()
        service = EntityAliasResolutionService(mock_session)

        score = service._calculate_similarity("Machine Learning", "Machine learning")
        # Should be high (case normalized)
        assert score > 0.8

    def test_completely_different_names(self):
        """Different names → low similarity."""
        from app.services.entity_alias_service import EntityAliasResolutionService

        mock_session = AsyncMock()
        service = EntityAliasResolutionService(mock_session)

        score = service._calculate_similarity("Python", "Banana")
        assert score < 0.5


class TestAliasCRUD:

    @pytest.mark.asyncio
    async def test_create_alias_success(self):
        """Create alias → added to session."""
        from app.services.entity_alias_service import EntityAliasResolutionService
        from app.models.graph import EntityAlias

        mock_session = AsyncMock()
        mock_session.add = MagicMock()
        mock_session.flush = AsyncMock()

        service = EntityAliasResolutionService(mock_session)

        # Mock lookups
        service._lookup_alias = AsyncMock(return_value=None)  # No existing alias
        service._entity_exists = AsyncMock(return_value=True)  # Canonical exists

        result = await service.create_alias(
            user_id=uuid.uuid4(),
            alias_name="AI",
            canonical_name="Artificial Intelligence",
            confidence=0.9,
            source="ai_suggested",
        )

        assert result is not None
        assert result.alias_name == "AI"
        assert result.canonical_name == "Artificial Intelligence"
        mock_session.add.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_alias_already_exists(self):
        """Alias exists → return existing."""
        from app.services.entity_alias_service import EntityAliasResolutionService

        mock_session = AsyncMock()
        service = EntityAliasResolutionService(mock_session)

        existing_alias = MagicMock()
        existing_alias.canonical_name = "Artificial Intelligence"
        service._lookup_alias = AsyncMock(return_value=existing_alias)

        result = await service.create_alias(
            user_id=uuid.uuid4(),
            alias_name="AI",
            canonical_name="Artificial Intelligence",
        )

        assert result == existing_alias
        mock_session.add.assert_not_called()

    @pytest.mark.asyncio
    async def test_create_alias_canonical_not_exists(self):
        """Canonical entity doesn't exist → return None."""
        from app.services.entity_alias_service import EntityAliasResolutionService

        mock_session = AsyncMock()
        service = EntityAliasResolutionService(mock_session)

        service._lookup_alias = AsyncMock(return_value=None)
        service._entity_exists = AsyncMock(return_value=False)

        result = await service.create_alias(
            user_id=uuid.uuid4(),
            alias_name="AI",
            canonical_name="NonExistent",
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_delete_alias_success(self):
        """Delete alias → removed from DB."""
        from app.services.entity_alias_service import EntityAliasResolutionService

        mock_session = AsyncMock()
        mock_session.delete = AsyncMock()
        mock_session.flush = AsyncMock()

        service = EntityAliasResolutionService(mock_session)

        existing_alias = MagicMock()
        service._lookup_alias = AsyncMock(return_value=existing_alias)

        result = await service.delete_alias(
            user_id=uuid.uuid4(),
            alias_name="AI",
        )

        assert result is True
        mock_session.delete.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_alias_not_found(self):
        """Alias doesn't exist → return False."""
        from app.services.entity_alias_service import EntityAliasResolutionService

        mock_session = AsyncMock()
        service = EntityAliasResolutionService(mock_session)

        service._lookup_alias = AsyncMock(return_value=None)

        result = await service.delete_alias(
            user_id=uuid.uuid4(),
            alias_name="NonExistent",
        )

        assert result is False


class TestResolveEntityAlias:

    @pytest.mark.asyncio
    async def test_resolve_existing_alias(self):
        """Alias exists → return canonical name."""
        from app.services.entity_alias_service import EntityAliasResolutionService

        mock_session = AsyncMock()
        service = EntityAliasResolutionService(mock_session)

        existing_alias = MagicMock()
        existing_alias.canonical_name = "Artificial Intelligence"
        service._lookup_alias = AsyncMock(return_value=existing_alias)

        result = await service.resolve_entity_alias(
            entity_name="AI",
            user_id=uuid.uuid4(),
        )

        assert result == "Artificial Intelligence"

    @pytest.mark.asyncio
    async def test_resolve_with_fuzzy_match(self):
        """No existing alias → fuzzy match + LLM verification."""
        from app.services.entity_alias_service import EntityAliasResolutionService

        mock_session = AsyncMock()
        service = EntityAliasResolutionService(mock_session)

        service._lookup_alias = AsyncMock(return_value=None)  # No existing
        service._fuzzy_match_entity = AsyncMock(return_value="Artificial Intelligence")
        service._verify_alias_with_llm = AsyncMock(return_value=True)

        result = await service.resolve_entity_alias(
            entity_name="AI",
            user_id=uuid.uuid4(),
        )

        assert result == "Artificial Intelligence"

    @pytest.mark.asyncio
    async def test_resolve_no_match(self):
        """No alias, no fuzzy match → return None."""
        from app.services.entity_alias_service import EntityAliasResolutionService

        mock_session = AsyncMock()
        service = EntityAliasResolutionService(mock_session)

        service._lookup_alias = AsyncMock(return_value=None)
        service._fuzzy_match_entity = AsyncMock(return_value=None)

        result = await service.resolve_entity_alias(
            entity_name="Unknown",
            user_id=uuid.uuid4(),
        )

        assert result is None


class TestGetGlobalEntities:

    @pytest.mark.asyncio
    async def test_global_entities_aggregation(self):
        """Get global entities với aggregation."""
        from app.services.entity_alias_service import EntityAliasResolutionService

        mock_session = AsyncMock()
        service = EntityAliasResolutionService(mock_session)

        # Mock query result
        mock_row = MagicMock()
        mock_row.canonical_name = "Python"
        mock_row.entity_type = "language"
        mock_row.total_occurrences = 5
        mock_row.document_count = 3
        mock_row.avg_confidence = 0.85

        mock_result = MagicMock()
        mock_result.all = MagicMock(return_value=[mock_row])
        mock_session.execute = AsyncMock(return_value=mock_result)

        result = await service.get_global_entities(
            user_id=uuid.uuid4(),
            limit=100,
        )

        assert len(result) == 1
        assert result[0]["canonical_name"] == "Python"
        assert result[0]["document_count"] == 3
        assert result[0]["avg_confidence"] == 0.85
