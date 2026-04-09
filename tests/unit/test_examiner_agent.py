"""
Unit tests cho ExaminerAgent.

Test coverage:
- generate_quiz: entity ranking, question generation, batch processing
- evaluate_quiz: scoring, weak areas detection
- convert_wrong_answers_to_flashcards: flashcard generation từ câu sai
- _rank_entities: centrality + confidence weighting
- _check_answer: answer validation
"""

import pytest
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

from app.core.examiner_agent import ExaminerAgent, _QuizResponse, _QuestionItem


# ============================================================
# Fixtures
# ============================================================

@pytest.fixture
def examiner():
    """ExaminerAgent instance cho tests."""
    return ExaminerAgent()


@pytest.fixture
def sample_entities():
    """Sample graph entities cho tests."""
    return [
        {"name": "Python", "entity_type": "language", "description": "Programming language", "confidence": 0.9},
        {"name": "FastAPI", "entity_type": "framework", "description": "Web framework for Python", "confidence": 0.85},
        {"name": "Django", "entity_type": "framework", "description": "Full-stack web framework", "confidence": 0.8},
        {"name": "Machine Learning", "entity_type": "concept", "description": "AI subset", "confidence": 0.75},
        {"name": "Neural Network", "entity_type": "concept", "description": "ML model", "confidence": 0.7},
    ]


@pytest.fixture
def sample_centrality():
    """Sample centrality scores."""
    return {
        "Python": 0.8,
        "FastAPI": 0.6,
        "Django": 0.5,
        "Machine Learning": 0.9,
        "Neural Network": 0.7,
    }


@pytest.fixture
def sample_relations():
    """Sample graph relations."""
    return [
        {"source_entity": "Python", "target_entity": "FastAPI", "relation_type": "used_by", "description": ""},
        {"source_entity": "Python", "target_entity": "Django", "relation_type": "used_by", "description": ""},
        {"source_entity": "Machine Learning", "target_entity": "Neural Network", "relation_type": "includes", "description": ""},
    ]


# ============================================================
# Tests cho _rank_entities
# ============================================================

class TestRankEntities:

    def test_rank_by_combined_score(self, examiner, sample_entities, sample_centrality):
        """Rank entities theo combined score (70% centrality + 30% confidence)."""
        ranked = examiner._rank_entities(sample_entities, sample_centrality)

        # Kiểm tra sorted descending
        scores = [e["combined_score"] for e in ranked]
        assert scores == sorted(scores, reverse=True)

        # Entity có centrality cao nhất nên đứng đầu
        # Machine Learning: 0.7*0.9 + 0.3*0.75 = 0.63 + 0.225 = 0.855
        assert ranked[0]["name"] == "Machine Learning"

    def test_combined_score_calculation(self, examiner):
        """Combined score = 0.7 * centrality + 0.3 * confidence."""
        entities = [{"name": "Test", "confidence": 0.5}]
        centrality = {"Test": 0.8}

        ranked = examiner._rank_entities(entities, centrality)

        expected = 0.7 * 0.8 + 0.3 * 0.5  # 0.56 + 0.15 = 0.71
        assert abs(ranked[0]["combined_score"] - expected) < 0.001

    def test_missing_centrality_defaults_to_zero(self, examiner):
        """Entity không có centrality → score = 0."""
        entities = [{"name": "Unknown", "confidence": 0.5}]
        centrality = {}  # Không có score

        ranked = examiner._rank_entities(entities, centrality)

        expected = 0.7 * 0.0 + 0.3 * 0.5  # 0.15
        assert abs(ranked[0]["combined_score"] - expected) < 0.001


# ============================================================
# Tests cho generate_quiz
# ============================================================

class TestGenerateQuiz:

    @pytest.mark.asyncio
    async def test_generate_quiz_limits_questions(self, examiner, sample_entities, sample_centrality, sample_relations):
        """num_questions không vượt quá MAX_QUIZ_QUESTIONS."""
        from app.constants import MAX_QUIZ_QUESTIONS

        with patch.object(examiner, "_generate_batch", new_callable=AsyncMock) as mock_batch:
            mock_batch.return_value = []

            questions = await examiner.generate_quiz(
                document_id=uuid.uuid4(),
                user_id=uuid.uuid4(),
                entities=sample_entities,
                centrality_scores=sample_centrality,
                graph_relations=sample_relations,
                num_questions=100,  # Vượt quá MAX_QUIZ_QUESTIONS
            )

            # Không nên tạo quá MAX_QUIZ_QUESTIONS questions
            assert len(questions) <= MAX_QUIZ_QUESTIONS

    @pytest.mark.asyncio
    async def test_generate_quiz_assigns_ids(self, examiner, sample_entities, sample_centrality, sample_relations):
        """Mỗi question có question_id và order."""
        # Mock batch generation
        with patch.object(examiner, "_generate_batch", new_callable=AsyncMock) as mock_batch:
            mock_batch.return_value = [
                {"entity_name": "Python", "question_text": "Q1?", "question_type": "multiple_choice", "correct_answer": "A"},
                {"entity_name": "FastAPI", "question_text": "Q2?", "question_type": "true_false", "correct_answer": "true"},
            ]

            questions = await examiner.generate_quiz(
                document_id=uuid.uuid4(),
                user_id=uuid.uuid4(),
                entities=sample_entities,
                centrality_scores=sample_centrality,
                graph_relations=sample_relations,
                num_questions=2,
            )

            assert len(questions) == 2
            assert all("question_id" in q for q in questions)
            assert all("order" in q for q in questions)
            assert questions[0]["order"] == 0
            assert questions[1]["order"] == 1

    @pytest.mark.asyncio
    async def test_generate_quiz_default_question_types(self, examiner, sample_entities, sample_centrality, sample_relations):
        """Không truyền question_types → default ['multiple_choice', 'true_false']."""
        with patch.object(examiner, "_generate_batch", new_callable=AsyncMock) as mock_batch:
            mock_batch.return_value = []

            await examiner.generate_quiz(
                document_id=uuid.uuid4(),
                user_id=uuid.uuid4(),
                entities=sample_entities,
                centrality_scores=sample_centrality,
                graph_relations=sample_relations,
                num_questions=5,
                # question_types=None
            )

            # _generate_batch được gọi với default types
            call_args = mock_batch.call_args
            assert call_args[1]["question_types"] == ["multiple_choice", "true_false"]


# ============================================================
# Tests cho evaluate_quiz
# ============================================================

class TestEvaluateQuiz:

    @pytest.mark.asyncio
    async def test_evaluate_quiz_all_correct(self, examiner):
        """Tất cả câu đúng → score = 100%."""
        questions = [
            {"question_id": "q1", "correct_answer": "A", "explanation": "", "entity_name": "Python", "bloom_level": "remember", "difficulty": 2},
            {"question_id": "q2", "correct_answer": "true", "explanation": "", "entity_name": "FastAPI", "bloom_level": "understand", "difficulty": 3},
        ]
        user_answers = [
            {"question_id": "q1", "answer": "A"},
            {"question_id": "q2", "answer": "true"},
        ]

        result = await examiner.evaluate_quiz(uuid.uuid4(), questions, user_answers)

        assert result["score"] == 100.0
        assert result["correct_count"] == 2
        assert result["wrong_count"] == 0
        assert result["weak_areas"] == []

    @pytest.mark.asyncio
    async def test_evaluate_quiz_all_wrong(self, examiner):
        """Tất cả câu sai → score = 0%, weak areas populated."""
        questions = [
            {"question_id": "q1", "correct_answer": "A", "explanation": "Exp 1", "entity_name": "Python", "entity_type": "language", "bloom_level": "remember", "difficulty": 2},
            {"question_id": "q2", "correct_answer": "true", "explanation": "Exp 2", "entity_name": "FastAPI", "entity_type": "framework", "bloom_level": "understand", "difficulty": 3},
        ]
        user_answers = [
            {"question_id": "q1", "answer": "B"},
            {"question_id": "q2", "answer": "false"},
        ]

        result = await examiner.evaluate_quiz(uuid.uuid4(), questions, user_answers)

        assert result["score"] == 0.0
        assert result["correct_count"] == 0
        assert result["wrong_count"] == 2
        assert len(result["weak_areas"]) == 2
        assert result["weak_areas"][0]["entity_name"] == "Python"

    @pytest.mark.asyncio
    async def test_evaluate_quiz_partial_correct(self, examiner):
        """50% đúng → score = 50%."""
        questions = [
            {"question_id": "q1", "correct_answer": "A", "explanation": "", "entity_name": "A", "bloom_level": "remember", "difficulty": 1},
            {"question_id": "q2", "correct_answer": "B", "explanation": "", "entity_name": "B", "bloom_level": "remember", "difficulty": 1},
        ]
        user_answers = [
            {"question_id": "q1", "answer": "A"},  # Correct
            {"question_id": "q2", "answer": "C"},  # Wrong
        ]

        result = await examiner.evaluate_quiz(uuid.uuid4(), questions, user_answers)

        assert result["score"] == 50.0
        assert result["correct_count"] == 1
        assert result["wrong_count"] == 1

    @pytest.mark.asyncio
    async def test_evaluate_quiz_weak_areas_limit(self, examiner):
        """Weak areas giới hạn tối đa 10."""
        questions = []
        user_answers = []

        # Tạo 15 câu, tất cả sai
        for i in range(15):
            questions.append({
                "question_id": f"q{i}",
                "correct_answer": "A",
                "explanation": f"Exp {i}",
                "entity_name": f"Entity{i}",
                "entity_type": "concept",
                "bloom_level": "remember",
                "difficulty": 1,
            })
            user_answers.append({"question_id": f"q{i}", "answer": "B"})

        result = await examiner.evaluate_quiz(uuid.uuid4(), questions, user_answers)

        assert result["wrong_count"] == 15
        assert len(result["weak_areas"]) == 10  # Giới hạn 10

    @pytest.mark.asyncio
    async def test_evaluate_quiz_empty(self, examiner):
        """Quiz rỗng → score = 0, total = 0."""
        result = await examiner.evaluate_quiz(uuid.uuid4(), [], [])

        assert result["score"] == 0
        assert result["total_questions"] == 0
        assert result["correct_count"] == 0
        assert result["wrong_count"] == 0


# ============================================================
# Tests cho convert_wrong_answers_to_flashcards
# ============================================================

class TestConvertWrongAnswersToFlashcards:

    def test_convert_all_wrong(self, examiner):
        """Tất cả câu sai → tạo flashcards."""
        quiz_result = {
            "results": [
                {
                    "is_correct": False,
                    "entity_name": "Python",
                    "explanation": "Python là ngôn ngữ lập trình",
                    "user_answer": "Java",
                    "correct_answer": "Python",
                    "question_id": "q1",
                },
            ]
        }

        flashcards = examiner.convert_wrong_answers_to_flashcards(quiz_result)

        assert len(flashcards) == 1
        assert "Python" in flashcards[0]["front"]
        assert "Python" in flashcards[0]["back"]
        assert flashcards[0]["metadata"]["source"] == "quiz_wrong_answer"

    def test_convert_no_wrong(self, examiner):
        """Không có câu sai → không tạo flashcards."""
        quiz_result = {
            "results": [
                {
                    "is_correct": True,
                    "entity_name": "Python",
                    "explanation": "",
                    "user_answer": "Python",
                    "correct_answer": "Python",
                    "question_id": "q1",
                },
            ]
        }

        flashcards = examiner.convert_wrong_answers_to_flashcards(quiz_result)

        assert flashcards == []

    def test_convert_mixed_results(self, examiner):
        """Chỉ câu sai mới tạo flashcards."""
        quiz_result = {
            "results": [
                {"is_correct": True, "entity_name": "A", "explanation": "", "user_answer": "A", "correct_answer": "A", "question_id": "q1"},
                {"is_correct": False, "entity_name": "B", "explanation": "Exp B", "user_answer": "X", "correct_answer": "B", "question_id": "q2"},
                {"is_correct": False, "entity_name": "C", "explanation": "Exp C", "user_answer": "Y", "correct_answer": "C", "question_id": "q3"},
            ]
        }

        flashcards = examiner.convert_wrong_answers_to_flashcards(quiz_result)

        assert len(flashcards) == 2
        assert all("B" in fc["back"] or "C" in fc["back"] for fc in flashcards)

    def test_convert_empty_results(self, examiner):
        """Results rỗng → không tạo flashcards."""
        flashcards = examiner.convert_wrong_answers_to_flashcards({"results": []})

        assert flashcards == []


# ============================================================
# Tests cho _check_answer
# ============================================================

class TestCheckAnswer:

    def test_multiple_choice_correct(self, examiner):
        """Multiple choice: answer khớp correct."""
        question = {"question_type": "multiple_choice", "correct_answer": "A"}
        assert examiner._check_answer(question, "A") is True

    def test_multiple_choice_incorrect(self, examiner):
        """Multiple choice: answer khác correct."""
        question = {"question_type": "multiple_choice", "correct_answer": "A"}
        assert examiner._check_answer(question, "B") is False

    def test_true_false_correct(self, examiner):
        """True/False: answer khớp correct."""
        question = {"question_type": "true_false", "correct_answer": "true"}
        assert examiner._check_answer(question, "true") is True

    def test_true_false_incorrect(self, examiner):
        """True/False: answer khác correct."""
        question = {"question_type": "true_false", "correct_answer": "false"}
        assert examiner._check_answer(question, "true") is False

    def test_check_answer_case_insensitive(self, examiner):
        """Answer check không phân biệt hoa thường."""
        question = {"question_type": "multiple_choice", "correct_answer": "a"}
        assert examiner._check_answer(question, "A") is True

    def test_check_answer_strips_whitespace(self, examiner):
        """Answer check loại bỏ whitespace."""
        question = {"question_type": "multiple_choice", "correct_answer": "A"}
        assert examiner._check_answer(question, "  A  ") is True
