"""
CrossVerificationService - Multi-document contradiction detection and consolidation.

This service analyzes information from multiple documents to:
1. Detect contradictions ("Document A says X, but Document B says Y")
2. Identify complementary info ("Document A mentions P, Document B extends with Q")
3. Generate consolidated context with source attribution per claim
"""

import uuid
import logging
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

from app.services.llm_service import llm_service
from app.constants import CROSS_VERIFICATION_CONTRADICTION_THRESHOLD

logger = logging.getLogger(__name__)


class CrossVerificationService:
    """
    Service for cross-document reasoning and verification.

    Provides:
    - Contradiction detection between documents
    - Complementary info identification
    - Consolidated context generation with source attribution
    - Claim verification across multiple sources
    """

    def __init__(self):
        self._contradiction_prompt = """You are an expert analyst comparing information from multiple sources.

Query: {query}

{documents_info}

Your task:
1. **Detect Contradictions**: Find statements that directly conflict between documents.
   - Example: "Document A says X, but Document B says Y"
   - Only report genuine contradictions, not minor differences.
   - Include severity: "high" (factual conflict), "medium" (interpretation conflict), "low" (nuance difference)

2. **Identify Complementary Info**: Find insights where documents extend each other.
   - Example: "Document A mentions P, Document B extends with Q"
   - Look for: elaborations, additional context, different perspectives, related concepts

3. **Assess Consensus**: Find points where documents agree.
   - Example: "Both documents agree that X is true"

Return a JSON object with this structure:
{{
  "contradictions": [
    {{
      "statement": "Clear description of the contradiction",
      "severity": "high|medium|low",
      "source_docs": ["doc_id_1", "doc_id_2"],
      "snippet_doc1": "Quote from doc1",
      "snippet_doc2": "Quote from doc2"
    }}
  ],
  "complementary": [
    {{
      "insight": "Description of how documents complement each other",
      "source_docs": ["doc_id_1", "doc_id_2"],
      "combined_understanding": "Synthesis of both sources"
    }}
  ],
  "consensus": [
    {{
      "point": "Point of agreement",
      "source_docs": ["doc_id_1", "doc_id_2"]
    }}
  ]
}}

Return ONLY valid JSON, no markdown, no extra text."""

        self._consolidation_prompt = """You are creating a consolidated summary from multiple sources with proper attribution.

Query: {query}

{documents_info}

Create a consolidated answer that:
1. Synthesizes information from all documents
2. Attributes each claim to its source document(s)
3. Notes contradictions where sources disagree
4. Highlights areas of consensus

Format as JSON:
{{
  "synthesized_answer": "Comprehensive answer combining all sources",
  "claims": [
    {{
      "claim": "Specific statement or fact",
      "sources": ["doc_id_1", "doc_id_2"],
      "confidence": "high|medium|low",
      "contradicted_by": ["doc_id_3"] or []
    }}
  ],
  "disagreements": [
    {{
      "topic": "What the disagreement is about",
      "positions": {{
        "doc_id_1": "What doc1 says",
        "doc_id_2": "What doc2 says"
      }}
    }}
  ]
}}

Return ONLY valid JSON, no markdown, no extra text."""

    async def cross_check(
        self,
        query: str,
        document_contexts: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Cross-check information across multiple documents.

        Args:
            query: User's original query
            document_contexts: List of dicts with:
                - document_id: str
                - document_title: str (optional)
                - context: List[Dict] from retriever.retrieve()

        Returns:
            Dict with contradictions, complementary, consensus, consolidated_answer
        """
        if len(document_contexts) < 2:
            # Single document - no cross-check needed
            return {
                "documents_analyzed": len(document_contexts),
                "contradictions": [],
                "complementary": [],
                "consensus": [],
                "consolidated_answer": "Only one document provided for analysis.",
                "claims": [],
                "disagreements": [],
            }

        # Extract key claims from each document
        claims_by_doc = self._extract_claims(document_contexts)

        # Build documents info for prompt
        docs_info = self._format_documents_for_prompt(claims_by_doc)

        # Detect contradictions, complementary info, and consensus
        analysis = await self._analyze_with_llm(
            query=query,
            docs_info=docs_info,
        )

        # Generate consolidated answer
        consolidation = await self._consolidate_with_llm(
            query=query,
            docs_info=docs_info,
            analysis=analysis,
        )

        return {
            "documents_analyzed": len(document_contexts),
            "contradictions": analysis.get("contradictions", []),
            "complementary": analysis.get("complementary", []),
            "consensus": analysis.get("consensus", []),
            "consolidated_answer": consolidation.get("synthesized_answer", ""),
            "claims": consolidation.get("claims", []),
            "disagreements": consolidation.get("disagreements", []),
        }

    def _extract_claims(
        self,
        document_contexts: List[Dict[str, Any]],
    ) -> Dict[str, Dict[str, Any]]:
        """
        Extract key claims from each document's context.
        Returns dict: document_id -> {title, claims[]}
        """
        claims_by_doc = {}

        for doc_ctx in document_contexts:
            doc_id = doc_ctx.get("document_id", "unknown")
            doc_title = doc_ctx.get("document_title", f"Document {doc_id[:8]}")
            context = doc_ctx.get("context", [])

            # Extract chunk content as claims
            claims = []
            for item in context:
                if item.get("type") == "chunk":
                    content = item.get("content", "")
                    # Take first 300 chars as claim snippet
                    claims.append(content[:300])

            claims_by_doc[doc_id] = {
                "title": doc_title,
                "claims": claims[:5],  # Top 5 claims per doc
            }

        return claims_by_doc

    def _format_documents_for_prompt(
        self,
        claims_by_doc: Dict[str, Dict[str, Any]],
    ) -> str:
        """Format claims into readable string for LLM prompt."""
        parts = []
        for doc_id, doc_info in claims_by_doc.items():
            title = doc_info.get("title", f"Document {doc_id[:8]}")
            claims = doc_info.get("claims", [])
            
            parts.append(f"**{title}** (ID: {doc_id}):")
            for idx, claim in enumerate(claims, 1):
                parts.append(f"  {idx}. {claim}")
            parts.append("")  # Blank line between docs

        return "\n".join(parts)

    async def _analyze_with_llm(
        self,
        query: str,
        docs_info: str,
    ) -> Dict[str, Any]:
        """Use LLM to detect contradictions, complementary info, and consensus."""
        
        class _ContradictionItem(BaseModel):
            statement: str = Field(..., description="Description of the contradiction")
            severity: str = Field(..., description="high, medium, or low")
            source_docs: List[str] = Field(..., description="Document IDs involved")
            snippet_doc1: str = Field(default="", description="Quote from first doc")
            snippet_doc2: str = Field(default="", description="Quote from second doc")

        class _ComplementaryItem(BaseModel):
            insight: str = Field(..., description="How documents complement each other")
            source_docs: List[str] = Field(..., description="Document IDs involved")
            combined_understanding: str = Field(..., description="Synthesis of both sources")

        class _ConsensusItem(BaseModel):
            point: str = Field(..., description="Point of agreement")
            source_docs: List[str] = Field(..., description="Document IDs that agree")

        class _CrossVerificationAnalysis(BaseModel):
            contradictions: List[_ContradictionItem] = Field(default_factory=list)
            complementary: List[_ComplementaryItem] = Field(default_factory=list)
            consensus: List[_ConsensusItem] = Field(default_factory=list)

        prompt = self._contradiction_prompt.format(
            query=query,
            documents_info=docs_info,
        )

        try:
            response = await llm_service.structured_extraction(
                prompt=prompt,
                response_model=_CrossVerificationAnalysis,
                max_retries=2,
            )

            if response:
                return {
                    "contradictions": [item.model_dump() for item in response.contradictions],
                    "complementary": [item.model_dump() for item in response.complementary],
                    "consensus": [item.model_dump() for item in response.consensus],
                }
        except Exception as e:
            logger.warning(f"LLM cross-verification failed: {e}")

        return {"contradictions": [], "complementary": [], "consensus": []}

    async def _consolidate_with_llm(
        self,
        query: str,
        docs_info: str,
        analysis: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Generate consolidated answer with source attribution."""

        class _ClaimItem(BaseModel):
            claim: str = Field(..., description="Specific statement or fact")
            sources: List[str] = Field(..., description="Document IDs supporting this claim")
            confidence: str = Field(..., description="high, medium, or low")
            contradicted_by: List[str] = Field(default_factory=list, description="Documents that contradict this")

        class _DisagreementItem(BaseModel):
            topic: str = Field(..., description="What the disagreement is about")
            positions: Dict[str, str] = Field(..., description="Map of doc_id -> position")

        class _ConsolidatedAnswer(BaseModel):
            synthesized_answer: str = Field(..., description="Comprehensive answer")
            claims: List[_ClaimItem] = Field(default_factory=list)
            disagreements: List[_DisagreementItem] = Field(default_factory=list)

        # Add analysis summary to prompt
        analysis_summary = f"- Contradictions found: {len(analysis.get('contradictions', []))}\n"
        analysis_summary += f"- Complementary insights: {len(analysis.get('complementary', []))}\n"
        analysis_summary += f"- Consensus points: {len(analysis.get('consensus', []))}"

        prompt = self._consolidation_prompt.format(
            query=query,
            documents_info=f"{docs_info}\n\nAnalysis Summary:\n{analysis_summary}",
        )

        try:
            response = await llm_service.structured_extraction(
                prompt=prompt,
                response_model=_ConsolidatedAnswer,
                max_retries=2,
            )

            if response:
                return {
                    "synthesized_answer": response.synthesized_answer,
                    "claims": [item.model_dump() for item in response.claims],
                    "disagreements": [item.model_dump() for item in response.disagreements],
                }
        except Exception as e:
            logger.warning(f"LLM consolidation failed: {e}")

        return {
            "synthesized_answer": "Unable to generate consolidated answer.",
            "claims": [],
            "disagreements": [],
        }


# Singleton instance
cross_verification_service = CrossVerificationService()
