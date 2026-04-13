"""
ExaminerAgent - AI-driven quiz generation from Knowledge Graph entities.

Uses graph centrality scores to select important entities,
then prompts LLM to generate quiz questions following Bloom's Taxonomy.
"""

import uuid
import json
import logging
from typing import List, Dict, Any, Optional

from app.services.llm_service import llm_service
from app.constants import (
    MAX_QUIZ_QUESTIONS,
)

logger = logging.getLogger(__name__)


class ExaminerAgent:
    """
    AI Agent that generates quizzes from knowledge graph entities.
    
    Follows Bloom's Taxonomy levels:
    - Remember: Recall facts (what, when, where)
    - Understand: Explain concepts (how, why)
    - Apply: Use knowledge in new situations
    - Analyze: Break down information, compare/contrast
    """

    def __init__(self):
        self._system_prompt = """You are an expert examiner creating educational quiz questions.
You must generate questions based on the provided entity information and follow strict JSON format.

For MULTIPLE_CHOICE questions:
- Provide exactly 4 options (A, B, C, D)
- Only ONE option is correct
- Distractors should be plausible but incorrect
- Distractors can be other entities from the same graph

For TRUE_FALSE questions:
- Provide a clear statement
- 50% should be true, 50% should be false
- The answer must be clearly true or false (not ambiguous)

Difficulty levels:
1 - Very Easy (basic recall)
2 - Easy (simple understanding)
3 - Medium (application)
4 - Hard (analysis)
5 - Very Hard (synthesis/evaluation)

Bloom's Taxonomy levels:
- remember: Recall facts
- understand: Explain concepts
- apply: Use knowledge
- analyze: Compare, contrast, break down
"""

    async def generate_quiz(
        self,
        document_id: uuid.UUID,
        user_id: uuid.UUID,
        entities: List[Dict[str, Any]],
        centrality_scores: Dict[str, float],
        graph_relations: List[Dict[str, Any]],
        topic: Optional[str] = None,
        num_questions: int = 10,
        question_types: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Generate quiz questions from graph entities.
        
        Args:
            document_id: Document to generate questions from
            user_id: User requesting the quiz
            entities: List of entity dicts with keys: id, name, description, entity_type, confidence
            centrality_scores: Dict mapping entity name -> centrality score
            graph_relations: List of relation dicts for distractor generation
            topic: Optional topic filter
            num_questions: Number of questions to generate
            question_types: List of question types ["multiple_choice", "true_false"]
        
        Returns:
            List of quiz question dicts ready for API response
        """
        if question_types is None:
            question_types = ["multiple_choice", "true_false"]

        # Limit questions to max
        num_questions = min(num_questions, MAX_QUIZ_QUESTIONS)

        # Rank entities by centrality score (importance)
        ranked_entities = self._rank_entities(entities, centrality_scores)

        # Select top entities for question generation
        selected_entities = ranked_entities[:num_questions]

        # Collect all entity names for distractor generation
        all_entity_names = [e["name"] for e in entities]

        # Build questions via LLM
        questions = []
        batch_size = 5  # Generate in batches for efficiency

        for i in range(0, len(selected_entities), batch_size):
            batch = selected_entities[i:i + batch_size]
            batch_questions = await self._generate_batch(
                entities=batch,
                all_entity_names=all_entity_names,
                graph_relations=graph_relations,
                question_types=question_types,
            )
            questions.extend(batch_questions)

        # Limit to requested number
        questions = questions[:num_questions]

        # Assign question IDs and order
        for idx, q in enumerate(questions):
            q["question_id"] = str(uuid.uuid4())
            q["order"] = idx

        logger.info(
            f"Generated {len(questions)} quiz questions for document {document_id}"
        )
        return questions

    async def evaluate_quiz(
        self,
        quiz_id: uuid.UUID,
        questions: List[Dict[str, Any]],
        user_answers: List[Dict[str, str]],
    ) -> Dict[str, Any]:
        """
        Evaluate quiz answers and calculate scores + weak areas.
        
        Args:
            quiz_id: Quiz ID
            questions: Original quiz questions
            user_answers: List of dicts with question_id and answer
            
        Returns:
            Dict with score, correct_count, wrong_count, weak_areas
        """
        correct_count = 0
        wrong_count = 0
        results = []
        weak_areas = []

        answers_map = {a["question_id"]: a["answer"] for a in user_answers}

        for question in questions:
            q_id = question["question_id"]
            user_answer = answers_map.get(q_id, "")
            correct_answer = question["correct_answer"]
            is_correct = self._check_answer(question, user_answer)

            result = {
                "question_id": q_id,
                "user_answer": user_answer,
                "correct_answer": correct_answer,
                "is_correct": is_correct,
                "explanation": question.get("explanation", ""),
                "entity_name": question.get("entity_name", ""),
                "bloom_level": question.get("bloom_level", "remember"),
                "difficulty": question.get("difficulty", 3),
            }
            results.append(result)

            if is_correct:
                correct_count += 1
            else:
                wrong_count += 1
                weak_areas.append({
                    "entity_name": question.get("entity_name", ""),
                    "entity_type": question.get("entity_type", ""),
                    "bloom_level": question.get("bloom_level", "remember"),
                })

        total = len(questions)
        score = (correct_count / total * 100) if total > 0 else 0

        return {
            "quiz_id": str(quiz_id),
            "score": round(score, 2),
            "correct_count": correct_count,
            "wrong_count": wrong_count,
            "total_questions": total,
            "results": results,
            "weak_areas": weak_areas[:10],  # Top 10 weak areas
        }

    def convert_wrong_answers_to_flashcards(
        self,
        quiz_result: Dict[str, Any],
    ) -> List[Dict[str, str]]:
        """
        Convert wrong answers to flashcard suggestions.
        
        Args:
            quiz_result: Result dict from evaluate_quiz()
            
        Returns:
            List of flashcard suggestions with front/back
        """
        flashcards = []

        for result in quiz_result.get("results", []):
            if not result["is_correct"]:
                entity_name = result.get("entity_name", "Unknown")
                explanation = result.get("explanation", "")
                user_answer = result.get("user_answer", "")
                correct_answer = result.get("correct_answer", "")

                front = f"What is {entity_name}?"
                back = f"{correct_answer}\n\nExplanation: {explanation}"

                if user_answer:
                    back += f"\n\n(Your answer was: {user_answer})"

                flashcards.append({
                    "front": front,
                    "back": back,
                    "metadata": {
                        "source": "quiz_wrong_answer",
                        "entity_name": entity_name,
                        "original_question": result.get("question_id", ""),
                    }
                })

        logger.info(
            f"Converted {len(flashcards)} wrong answers to flashcard suggestions"
        )
        return flashcards

    # ========== Private Methods ==========

    def _rank_entities(
        self,
        entities: List[Dict[str, Any]],
        centrality_scores: Dict[str, float],
    ) -> List[Dict[str, Any]]:
        """
        Rank entities by centrality score + confidence.
        Returns sorted list (highest score first).
        """
        ranked = []
        for entity in entities:
            name = entity["name"]
            centrality = centrality_scores.get(name, 0.0)
            confidence = entity.get("confidence", 0.5)

            # Combined score: 70% centrality + 30% confidence
            combined_score = (0.7 * centrality) + (0.3 * confidence)

            ranked.append({
                **entity,
                "combined_score": combined_score,
                "centrality_score": centrality,
            })

        # Sort by combined score descending
        ranked.sort(key=lambda x: x["combined_score"], reverse=True)
        return ranked

    async def _generate_batch(
        self,
        entities: List[Dict[str, Any]],
        all_entity_names: List[str],
        graph_relations: List[Dict[str, Any]],
        question_types: List[str],
    ) -> List[Dict[str, Any]]:
        """
        Generate quiz questions for a batch of entities via LLM.
        """
        # Build prompt with entity info and distractors
        entity_descriptions = "\n".join([
            f"- **{e['name']}** ({e.get('entity_type', 'concept')}): {e.get('description', '')}"
            for e in entities
        ])

        # Get related entities for each entity (for distractor generation)
        related_map = {}
        for rel in graph_relations:
            source = rel.get("source_entity", rel.get("source_entity_id", ""))
            target = rel.get("target_entity", rel.get("target_entity_id", ""))
            if source not in related_map:
                related_map[source] = []
            if target not in related_map[source]:
                related_map[source].append(target)

        related_entities_json = json.dumps(related_map, indent=2)

        # Alternate question types
        types_cycle = question_types * 3  # Repeat types

        prompt = f"""Generate quiz questions for the following entities:

{entity_descriptions}

Related entities (for distractors):
{related_entities_json}

Generate exactly {len(entities)} questions.
Distribute question types: {question_types}

Return a JSON array with this exact structure:
[
  {{
    "entity_name": "Entity Name",
    "question_text": "The actual question?",
    "question_type": "multiple_choice",
    "difficulty": 3,
    "bloom_level": "remember",
    "options": ["Option A", "Option B", "Option C", "Option D"],
    "correct_answer": "Option A",
    "explanation": "Brief explanation of why this is correct"
  }},
  {{
    "entity_name": "Entity Name",
    "question_text": "True/False statement?",
    "question_type": "true_false",
    "difficulty": 2,
    "bloom_level": "understand",
    "correct_answer": "true",
    "explanation": "Brief explanation"
  }}
]

Rules:
1. Each question must be about ONE entity
2. For multiple_choice: provide exactly 4 options, only 1 correct
3. For true_false: correct_answer must be "true" or "false" (lowercase)
4. Difficulty: 1-5
5. Bloom level: remember, understand, apply, analyze
6. Use related entities as distractors for multiple choice
7. Explanations should be clear and educational

Return ONLY valid JSON array, no markdown, no extra text."""

        response = await llm_service.structured_extraction(
            prompt=prompt,
            response_model=_QuizResponse,
            max_retries=3,
        )

        if response is None or not response.questions:
            logger.warning("LLM returned empty quiz response")
            return []

        questions = []
        for q in response.questions:
            question_dict = q.model_dump()
            # Ensure all required fields exist
            question_dict.setdefault("options", [])
            question_dict.setdefault("explanation", "")
            questions.append(question_dict)

        return questions

    def _check_answer(
        self,
        question: Dict[str, Any],
        user_answer: str,
    ) -> bool:
        """
        Check if user answer matches correct answer.
        """
        correct = question.get("correct_answer", "").strip().lower()
        user = user_answer.strip().lower()

        if question.get("question_type") == "true_false":
            return user in ("true", "false") and user == correct
        else:
            # Multiple choice: match by letter or content
            return user == correct


# Pydantic models for structured LLM output
from pydantic import BaseModel, Field


class _QuestionItem(BaseModel):
    entity_name: str = Field(..., description="The entity this question is about")
    question_text: str = Field(..., description="The actual question text")
    question_type: str = Field(..., description="multiple_choice or true_false")
    difficulty: int = Field(..., ge=1, le=5, description="Difficulty level 1-5")
    bloom_level: str = Field(..., description="remember, understand, apply, analyze")
    options: Optional[List[str]] = Field(
        default=None, description="Options for multiple choice (4 items)"
    )
    correct_answer: str = Field(..., description="The correct answer")
    explanation: str = Field(..., description="Explanation of the correct answer")


class _QuizResponse(BaseModel):
    questions: List[_QuestionItem] = Field(..., description="List of generated questions")


# Singleton instance
examiner_agent = ExaminerAgent()
