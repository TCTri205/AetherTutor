"""
Quiz API endpoints - Stage 2: The Examiner Agent & Quiz Generation

Endpoints:
- POST /api/v1/quiz/generate - Generate quiz from document graph
- POST /api/v1/quiz/{quiz_id}/submit - Submit quiz answers
- GET  /api/v1/quiz/results/{result_id} - Get quiz result detail
- GET  /api/v1/quiz/{quiz_id}/results - List quiz results (history)
- GET  /api/v1/quiz - List user's quizzes
- GET  /api/v1/quiz/{quiz_id} - Get quiz detail
- POST /api/v1/quiz/results/{result_id}/convert-to-flashcards - Convert wrong answers to flashcards
- POST /api/v1/quiz/results/{result_id}/feedback - Submit quality feedback
- GET  /api/v1/quiz/stats - Get user's quiz statistics
- GET  /api/v1/quiz/weak-areas - Get top weak areas across all quizzes
"""

import uuid
import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.api.dependencies import get_current_user_id
from app.repositories.quiz_repo import (
    QuizRepository,
    QuizResultRepository,
    QuizAnswerRepository,
)
from app.repositories.graph_repo import GraphRepository
from app.repositories.document_repo import DocumentRepository
from app.core.examiner_agent import examiner_agent
from app.core.graph_builder import GraphBuilder
from app.services.quiz_analysis_service import QuizAnalysisService
from app.schemas.quiz import (
    QuizGenerateRequest,
    QuizSubmitRequest,
    QuizFeedbackRequest,
    QuizResponse,
    QuizQuestionResponse,
    QuizResultResponse,
    QuizAnswerResponse,
    WeakAreaResponse,
    QuizStatsResponse,
    QuizListItemResponse,
    QuizResultListItemResponse,
    FlashcardSuggestionResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/quiz", tags=["Quiz"])


# ===== Quiz Generation =====

@router.post("/generate", response_model=QuizResponse)
async def generate_quiz(
    request: QuizGenerateRequest,
    user_id: str = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_db),
):
    """
    Generate a quiz from document's knowledge graph.
    
    Uses ExaminerAgent to create questions based on entity centrality and confidence.
    """
    # Validate document
    if not request.document_id:
        raise HTTPException(status_code=400, detail="document_id is required")

    doc_uuid = uuid.UUID(request.document_id)
    doc_repo = DocumentRepository(session)
    document = await doc_repo.get_by_id_with_user(doc_uuid, uuid.UUID(user_id))

    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    # Get graph entities and relations
    graph_repo = GraphRepository(session)
    entities = await graph_repo.get_entities_by_document(
        doc_uuid, min_confidence=0.0, limit=50
    )

    if not entities:
        raise HTTPException(
            status_code=400,
            detail="Document has no extracted entities. Please wait for processing.",
        )

    relations = await graph_repo.get_all_relations(doc_uuid)
    relations_data = [
        {
            "source_entity": r.source_entity.canonical_name,
            "target_entity": r.target_entity.canonical_name,
            "relation_type": r.relation_type,
        }
        for r in relations
    ]

    # Get centrality scores using GraphBuilder
    builder = GraphBuilder()
    all_entities_for_graph = await graph_repo.get_all_entities(doc_uuid)
    entity_names = [e.canonical_name for e in all_entities_for_graph]

    # Build temporary graph for centrality calculation
    await builder.add_entities_and_relations(
        entities=[{"name": name} for name in entity_names],
        relations=relations_data,
        document_id=str(doc_uuid),
    )
    centrality_data = builder.get_centrality_scores(str(doc_uuid))
    # Extract degree_centrality as primary score
    centrality_scores = {
        name: data.get("degree_centrality", 0.0)
        for name, data in centrality_data.items()
    }

    # Generate quiz using ExaminerAgent
    questions = await examiner_agent.generate_quiz(
        document_id=doc_uuid,
        user_id=uuid.UUID(user_id),
        entities=entities,
        centrality_scores=centrality_scores,
        graph_relations=relations_data,
        topic=request.topic,
        num_questions=request.num_questions,
        question_types=request.question_types,
    )

    if not questions:
        raise HTTPException(
            status_code=500,
            detail="Failed to generate quiz questions. Please try again.",
        )

    # Save quiz to database
    quiz_repo = QuizRepository(session)
    quiz_title = f"Quiz: {document.filename}"
    if request.topic:
        quiz_title += f" - {request.topic}"

    quiz = await quiz_repo.create_quiz(
        user_id=uuid.UUID(user_id),
        document_id=doc_uuid,
        title=quiz_title,
        questions=questions,
        topic=request.topic,
        question_types=request.question_types,
        difficulty=request.difficulty,
    )

    # Build response (without correct answers)
    quiz_questions = [
        QuizQuestionResponse(
            question_id=q["question_id"],
            order=q.get("order", idx),
            entity_name=q.get("entity_name", ""),
            question_text=q["question_text"],
            question_type=q["question_type"],
            difficulty=q.get("difficulty", 3),
            bloom_level=q.get("bloom_level", "remember"),
            options=q.get("options"),
        )
        for idx, q in enumerate(questions)
    ]

    return QuizResponse(
        id=str(quiz.id),
        user_id=str(quiz.user_id),
        document_id=str(quiz.document_id) if quiz.document_id else None,
        title=quiz.title,
        description=quiz.description,
        topic=quiz.topic,
        num_questions=quiz.num_questions,
        question_types=quiz.question_types,
        difficulty=quiz.difficulty,
        questions=quiz_questions,
        created_at=quiz.created_at,
    )


# ===== Quiz Submission =====

@router.post("/{quiz_id}/submit", response_model=QuizResultResponse)
async def submit_quiz(
    quiz_id: str,
    request: QuizSubmitRequest,
    user_id: str = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_db),
):
    """
    Submit quiz answers for grading.
    
    Returns detailed results with correct/wrong indicators and explanations.
    """
    quiz_uuid = uuid.UUID(quiz_id)
    quiz_repo = QuizRepository(session)
    quiz = await quiz_repo.get_by_id_with_questions(quiz_uuid)

    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found")

    if str(quiz.user_id) != user_id:
        raise HTTPException(status_code=403, detail="Not your quiz")

    # Get questions from quiz metadata
    questions = quiz.quiz_metadata.get("questions", [])
    if not questions:
        raise HTTPException(status_code=400, detail="Quiz has no questions")

    # Evaluate answers
    evaluation = await examiner_agent.evaluate_quiz(
        quiz_id=quiz_uuid,
        questions=questions,
        user_answers=request.answers,
    )

    # Save result
    result_repo = QuizResultRepository(session)
    result = await result_repo.create_result(
        user_id=uuid.UUID(user_id),
        quiz_id=quiz_uuid,
        score=evaluation["score"],
        total_questions=evaluation["total_questions"],
        correct_answers=evaluation["correct_count"],
        weak_areas=evaluation.get("weak_areas", []),
    )

    # Save individual answers
    answer_repo = QuizAnswerRepository(session)
    answer_records = []
    for answer_result in evaluation["results"]:
        # Find original question
        question = next(
            (q for q in questions if q["question_id"] == answer_result["question_id"]),
            None,
        )
        if not question:
            continue

        answer_record = {
            "user_id": uuid.UUID(user_id),
            "quiz_result_id": result.id,
            "question_index": question.get("order", 0),
            "question_text": question["question_text"],
            "question_type": question["question_type"],
            "user_answer": answer_result["user_answer"],
            "correct_answer": question["correct_answer"],
            "is_correct": answer_result["is_correct"],
            "explanation": answer_result.get("explanation", ""),
            "entity_name": question.get("entity_name", ""),
            "difficulty": question.get("difficulty", 3),
        }
        answer_records.append(answer_record)

    # Bulk insert answers
    from app.models.quiz import QuizAnswer
    answer_objects = [QuizAnswer(**a) for a in answer_records]
    await answer_repo.bulk_create_answers(answer_objects)

    # Build response
    answer_responses = [
        QuizAnswerResponse(
            question_id=r["question_id"],
            question_text=r.get("question_text", ""),
            question_type=r.get("question_type", ""),
            user_answer=r["user_answer"],
            correct_answer=r["correct_answer"],
            is_correct=r["is_correct"],
            explanation=r.get("explanation"),
            entity_name=r.get("entity_name"),
            bloom_level=r.get("bloom_level", "remember"),
            difficulty=r.get("difficulty", 3),
        )
        for r in evaluation["results"]
    ]

    weak_area_responses = [
        WeakAreaResponse(
            entity_name=wa.get("entity_name", ""),
            entity_type=wa.get("entity_type", ""),
            bloom_level=wa.get("bloom_level", "remember"),
        )
        for wa in evaluation.get("weak_areas", [])
    ]

    return QuizResultResponse(
        id=str(result.id),
        quiz_id=str(result.quiz_id),
        score=result.score,
        correct_count=result.correct_answers,
        wrong_count=result.total_questions - result.correct_answers,
        total_questions=result.total_questions,
        results=answer_responses,
        weak_areas=weak_area_responses,
        completed_at=result.completed_at,
    )


# ===== Quiz Results =====

@router.get("/results/{result_id}", response_model=QuizResultResponse)
async def get_quiz_result(
    result_id: str,
    user_id: str = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_db),
):
    """
    Get detailed quiz results with explanations and weak areas.
    """
    result_uuid = uuid.UUID(result_id)
    result_repo = QuizResultRepository(session)
    result = await result_repo.get_by_id_with_answers(result_uuid)

    if not result:
        raise HTTPException(status_code=404, detail="Quiz result not found")

    if str(result.user_id) != user_id:
        raise HTTPException(status_code=403, detail="Not your quiz result")

    # Build response
    answer_responses = [
        QuizAnswerResponse(
            question_id=str(a.id),
            question_text=a.question_text,
            question_type=a.question_type,
            user_answer=a.user_answer if isinstance(a.user_answer, str) else str(a.user_answer),
            correct_answer=a.correct_answer if isinstance(a.correct_answer, str) else str(a.correct_answer),
            is_correct=a.is_correct,
            explanation=a.explanation,
            entity_name=a.entity_name,
            bloom_level="remember",  # TODO: Store bloom level in answer model
            difficulty=a.difficulty,
        )
        for a in result.answers
    ]

    weak_area_responses = [
        WeakAreaResponse(
            entity_name=wa.get("entity_name", ""),
            entity_type=wa.get("entity_type", ""),
            bloom_level=wa.get("bloom_level", "remember"),
        )
        for wa in (result.weak_areas or [])
    ]

    return QuizResultResponse(
        id=str(result.id),
        quiz_id=str(result.quiz_id),
        score=result.score,
        correct_count=result.correct_answers,
        wrong_count=result.total_questions - result.correct_answers,
        total_questions=result.total_questions,
        results=answer_responses,
        weak_areas=weak_area_responses,
        completed_at=result.completed_at,
    )


@router.get("/{quiz_id}/results", response_model=list[QuizResultListItemResponse])
async def list_quiz_results(
    quiz_id: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    user_id: str = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_db),
):
    """
    List all quiz results (history) for a specific quiz.

    Returns summary of each attempt with score and completion time.
    """
    quiz_uuid = uuid.UUID(quiz_id)

    # Verify quiz ownership
    quiz_repo = QuizRepository(session)
    quiz = await quiz_repo.get_by_id_with_questions(quiz_uuid)
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found")
    if str(quiz.user_id) != user_id:
        raise HTTPException(status_code=403, detail="Not your quiz")

    # Get results for this quiz
    result_repo = QuizResultRepository(session)
    results = await result_repo.get_by_user(
        uuid.UUID(user_id), skip=skip, limit=limit, quiz_id=quiz_uuid
    )

    return [
        QuizResultListItemResponse(
            id=str(r.id),
            quiz_id=str(r.quiz_id),
            quiz_title=quiz.title,
            score=r.score,
            correct_answers=r.correct_answers,
            total_questions=r.total_questions,
            completed_at=r.completed_at,
        )
        for r in results
    ]


# ===== Quiz List & Detail =====

@router.get("", response_model=list[QuizListItemResponse])
async def list_quizzes(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    document_id: Optional[str] = None,
    user_id: str = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_db),
):
    """List user's quizzes with pagination."""
    quiz_repo = QuizRepository(session)
    doc_uuid = uuid.UUID(document_id) if document_id else None

    quizzes = await quiz_repo.get_by_user(
        uuid.UUID(user_id), skip=skip, limit=limit, document_id=doc_uuid
    )

    return [
        QuizListItemResponse(
            id=str(q.id),
            title=q.title,
            topic=q.topic,
            num_questions=q.num_questions,
            difficulty=q.difficulty,
            created_at=q.created_at,
        )
        for q in quizzes
    ]


@router.get("/{quiz_id}", response_model=QuizResponse)
async def get_quiz(
    quiz_id: str,
    user_id: str = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_db),
):
    """Get quiz detail with questions."""
    quiz_uuid = uuid.UUID(quiz_id)
    quiz_repo = QuizRepository(session)
    quiz = await quiz_repo.get_by_id_with_questions(quiz_uuid)

    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found")

    if str(quiz.user_id) != user_id:
        raise HTTPException(status_code=403, detail="Not your quiz")

    questions = quiz.quiz_metadata.get("questions", [])
    quiz_questions = [
        QuizQuestionResponse(
            question_id=q["question_id"],
            order=q.get("order", idx),
            entity_name=q.get("entity_name", ""),
            question_text=q["question_text"],
            question_type=q["question_type"],
            difficulty=q.get("difficulty", 3),
            bloom_level=q.get("bloom_level", "remember"),
            options=q.get("options"),
        )
        for idx, q in enumerate(questions)
    ]

    return QuizResponse(
        id=str(quiz.id),
        user_id=str(quiz.user_id),
        document_id=str(quiz.document_id) if quiz.document_id else None,
        title=quiz.title,
        description=quiz.description,
        topic=quiz.topic,
        num_questions=quiz.num_questions,
        question_types=quiz.question_types,
        difficulty=quiz.difficulty,
        questions=quiz_questions,
        created_at=quiz.created_at,
    )


# ===== Flashcard Conversion =====

@router.post("/results/{result_id}/convert-to-flashcards")
async def convert_to_flashcards(
    result_id: str,
    user_id: str = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_db),
):
    """
    Convert wrong answers from a quiz into flashcard suggestions.
    
    Returns list of flashcard suggestions that can be created manually.
    """
    result_uuid = uuid.UUID(result_id)
    result_repo = QuizResultRepository(session)
    result = await result_repo.get_by_id_with_answers(result_uuid)

    if not result:
        raise HTTPException(status_code=404, detail="Quiz result not found")

    if str(result.user_id) != user_id:
        raise HTTPException(status_code=403, detail="Not your quiz result")

    # Get quiz questions for context
    quiz_repo = QuizRepository(session)
    quiz = await quiz_repo.get_by_id_with_questions(result.quiz_id)
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found")

    questions = quiz.quiz_metadata.get("questions", [])

    # Evaluate again to get wrong answers
    evaluation = await examiner_agent.evaluate_quiz(
        quiz_id=result.quiz_id,
        questions=questions,
        user_answers=[
            {"question_id": str(a.id), "answer": str(a.user_answer)}
            for a in result.answers
        ],
    )

    # Convert wrong answers to flashcards
    flashcards = examiner_agent.convert_wrong_answers_to_flashcards(evaluation)

    return {
        "result_id": str(result.id),
        "flashcard_suggestions": [
            FlashcardSuggestionResponse(
                front=fc["front"],
                back=fc["back"],
                metadata=fc.get("metadata", {}),
            )
            for fc in flashcards
        ],
        "total_suggestions": len(flashcards),
    }


# ===== Quality Feedback =====

@router.post("/results/{result_id}/feedback")
async def submit_feedback(
    result_id: str,
    request: QuizFeedbackRequest,
    user_id: str = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_db),
):
    """
    Submit quality feedback for a quiz result.

    Feedback is used to improve future quiz generation.
    Low ratings (<= threshold) trigger ARQ analysis job.
    """
    result_uuid = uuid.UUID(result_id)
    result_repo = QuizResultRepository(session)
    result = await result_repo.get_by_id_with_answers(result_uuid)

    if not result:
        raise HTTPException(status_code=404, detail="Quiz result not found")

    if str(result.user_id) != user_id:
        raise HTTPException(status_code=403, detail="Not your quiz result")

    await result_repo.update_quality_feedback(
        result_id=result_uuid,
        quality_rating=request.quality_rating,
        quality_feedback=request.quality_feedback,
    )

    # Trigger ARQ job if low rating
    if request.quality_rating <= 2:  # QUIZ_FEEDBACK_FLAG_THRESHOLD
        try:
            from app.worker.queue import get_redis_pool
            from arq import ArqRedis

            pool: ArqRedis = await get_redis_pool()
            await pool.enqueue_job(
                "quiz_feedback_analysis_task",
                str(result_uuid),
                _job_id=f"quiz_feedback:{result_uuid}",
            )
        except Exception as e:
            # Log error but don't fail the request
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to enqueue quiz feedback analysis: {e}")

    return {
        "status": "success",
        "message": "Feedback submitted successfully",
        "quality_rating": request.quality_rating,
    }


# ===== Statistics =====

@router.get("/stats", response_model=QuizStatsResponse)
async def get_quiz_stats(
    user_id: str = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_db),
):
    """Get user's quiz statistics."""
    result_repo = QuizResultRepository(session)
    stats = await result_repo.get_stats(uuid.UUID(user_id))

    return QuizStatsResponse(**stats)


@router.get("/weak-areas", response_model=list[WeakAreaResponse])
async def get_weak_areas(
    limit: int = Query(10, ge=1, le=50),
    user_id: str = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_db),
):
    """
    Get top weak areas across all quizzes.
    
    Entities that user got wrong most frequently.
    """
    result_repo = QuizResultRepository(session)
    weak_areas = await result_repo.get_weak_areas(uuid.UUID(user_id), limit=limit)

    return [
        WeakAreaResponse(
            entity_name=wa["entity_name"],
            entity_type="",  # TODO: Fetch entity type from graph
            bloom_level="remember",  # Default
        )
        for wa in weak_areas
    ]
