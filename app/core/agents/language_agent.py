"""
Language Agent - Specialized agent for language learning.

Capabilities:
- Vocabulary extraction from documents
- Grammar pattern analysis
- Conjugation tables
- Translation exercises
- Grammar checking
"""

from typing import Dict, Any, List, Optional
from pydantic import BaseModel

from .base_agent import BaseAgent, AgentCapabilities


class VocabularyItem(BaseModel):
    """Vocabulary item."""
    word: str
    definition: str
    example: str
    part_of_speech: str
    frequency: str = "common"  # common, uncommon, rare


class GrammarPattern(BaseModel):
    """Grammar pattern explanation."""
    pattern: str
    description: str
    examples: List[str]
    difficulty: str = "beginner"  # beginner, intermediate, advanced


class ConjugationTable(BaseModel):
    """Verb conjugation table."""
    verb: str
    tense: str
    conjugations: Dict[str, str]  # pronoun -> conjugated form


class LanguageResponse(BaseModel):
    """Structured response from Language Agent."""
    vocabulary: List[VocabularyItem] = []
    grammar_patterns: List[GrammarPattern] = []
    conjugation_tables: List[ConjugationTable] = []
    translations: List[Dict[str, str]] = []
    exercises: List[Dict[str, str]] = []
    explanation: str = ""


class LanguageAgent(BaseAgent):
    """
    Specialized agent for language learning.
    
    Features:
    - Extract vocabulary from uploaded texts
    - Analyze grammar patterns
    - Generate conjugation tables
    - Create translation exercises
    - Check grammar
    
    Usage:
        agent = LanguageAgent()
        result = await agent.execute(
            text="Some French text...",
            target_language="french",
            task="vocabulary"
        )
    """
    
    name = "language_agent"
    version = "1.0.0"
    description = "Expert ngôn ngữ - Hỗ trợ học từ vựng, ngữ pháp, dịch thuật"
    icon = "🌍"
    author = "AetherTutor"
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._supported_languages = [
            "english", "french", "spanish", "german", "italian",
            "portuguese", "russian", "chinese", "japanese", "korean",
            "vietnamese"
        ]
    
    def _default_system_prompt(self) -> str:
        return """Bạn là Language Agent - chuyên gia dạy ngôn ngữ.

NHIỆM VỤ:
1. Trích xuất từ vựng quan trọng từ văn bản
2. Phân tích mẫu ngữ pháp
3. Tạo bảng chia động từ
4. Tạo bài tập dịch thuật
5. Kiểm tra ngữ pháp

PHƯƠNG PHÁP:
- Sử dụng phương pháp Socratic để dạy
- Giải thích ngắn gọn, dễ hiểu
- Đưa ra ví dụ thực tế
- Tạo exercises phù hợp trình độ

ĐỊNH DẠNG TRẢ VỀ:
Luôn trả về JSON với cấu trúc:
{
  "vocabulary": [{"word", "definition", "example", "part_of_speech", "frequency"}],
  "grammar_patterns": [{"pattern", "description", "examples", "difficulty"}],
  "conjugation_tables": [{"verb", "tense", "conjugations"}],
  "translations": [{"source", "target"}],
  "exercises": [{"question", "answer", "hint"}],
  "explanation": "Giải thích chi tiết"
}"""
    
    def get_capabilities(self) -> List[AgentCapabilities]:
        return [
            AgentCapabilities.LANGUAGE_LEARNING,
            AgentCapabilities.TRANSLATION,
            AgentCapabilities.GRAMMAR_CHECK,
            AgentCapabilities.FLASHCARD_CREATION,
        ]
    
    async def execute(self, **kwargs) -> Dict[str, Any]:
        """
        Execute language learning task.
        
        Args:
            text: Input text to analyze
            target_language: Target language (e.g., "french")
            task: Task type (vocabulary, grammar, translation, conjugation, exercise, check)
            source_language: Source language for translation (default: english)
            difficulty: Difficulty level (beginner, intermediate, advanced)
            
        Returns:
            Dict with language analysis result
        """
        text = kwargs.get("text", "")
        target_language = kwargs.get("target_language", "english")
        task = kwargs.get("task", "vocabulary")
        source_language = kwargs.get("source_language", "english")
        difficulty = kwargs.get("difficulty", "beginner")
        
        if not text:
            return {"error": "No text provided", "status": "failed"}
        
        if target_language not in self._supported_languages:
            return {
                "error": f"Unsupported language: {target_language}",
                "supported": self._supported_languages,
                "status": "failed"
            }
        
        # Build prompt based on task
        prompt = self._build_prompt(text, target_language, source_language, task, difficulty)
        
        try:
            # Call LLM with structured extraction
            result = await self._call_llm_structured(
                prompt=prompt,
                response_model=LanguageResponse,
                max_retries=2,
            )
            
            if result:
                return {
                    "status": "success",
                    "task": task,
                    "language": target_language,
                    "result": result.model_dump(),
                }
            else:
                # Fallback: use regular LLM call
                response = await self._call_llm([
                    {"role": "user", "content": prompt}
                ])
                
                return {
                    "status": "success",
                    "task": task,
                    "language": target_language,
                    "result": {"explanation": response},
                }
        
        except Exception as e:
            return {
                "error": str(e),
                "status": "failed",
                "task": task,
            }
    
    def _build_prompt(
        self,
        text: str,
        target_language: str,
        source_language: str,
        task: str,
        difficulty: str
    ) -> str:
        """Build task-specific prompt."""
        
        prompts = {
            "vocabulary": f"""Phân tích văn bản sau và trích xuất 10-15 từ vựng quan trọng nhất.

Ngôn ngữ mục tiêu: {target_language}
Mức độ: {difficulty}

Văn bản:
{text}

Trả về danh sách vocabulary với: word, definition, example, part_of_speech, frequency.""",
            
            "grammar": f"""Phân tích mẫu ngữ pháp trong văn bản sau.

Ngôn ngữ: {target_language}
Mức độ: {difficulty}

Văn bản:
{text}

Trả về grammar_patterns với: pattern, description, examples, difficulty.""",
            
            "conjugation": f"""Tạo bảng chia động từ cho các động từ trong văn bản.

Ngôn ngữ: {target_language}
Thì: present, past, future (nếu có)

Văn bản:
{text}

Trả về conjugation_tables với: verb, tense, conjugations.""",
            
            "translation": f"""Dịch văn bản sau từ {source_language} sang {target_language}.

Văn bản:
{text}

Trả về translations với: source, target.
Kèm theo giải thích các điểm ngữ pháp/từ vựng quan trọng.""",
            
            "exercise": f"""Tạo 5-10 bài tập luyện ngôn ngữ {target_language} dựa trên văn bản sau.

Mức độ: {difficulty}
Loại bài tập: trắc nghiệm, điền vào chỗ trống, dịch thuật

Văn bản:
{text}

Trả về exercises với: question, answer, hint.""",
            
            "check": f"""Kiểm tra ngữ pháp của văn bản sau (ngôn ngữ: {target_language}).

Văn bản:
{text}

Trả về:
- Các lỗi ngữ pháp (nếu có)
- Gợi ý sửa lỗi
- Giải thích chi tiết""",
        }
        
        return prompts.get(task, prompts["vocabulary"])
