"""
Math Agent - Specialized agent for mathematics tutoring.

Capabilities:
- Step-by-step solutions
- LaTeX rendering
- Formula extraction from documents
- Symbolic computation hints
- Problem solving with Socratic method
"""

from typing import Dict, Any, List
from pydantic import BaseModel

from .base_agent import BaseAgent, AgentCapabilities


class MathStep(BaseModel):
    """Step in a solution."""
    step_number: int
    description: str
    formula: str = ""  # LaTeX formula
    explanation: str = ""


class FormulaItem(BaseModel):
    """Extracted formula."""
    name: str
    latex: str
    variables: Dict[str, str]  # variable -> description
    context: str = ""


class MathResponse(BaseModel):
    """Structured response from Math Agent."""
    problem: str = ""
    solution_steps: List[MathStep] = []
    formulas: List[FormulaItem] = []
    hints: List[str] = []
    explanation: str = ""
    difficulty: str = "medium"
    topic: str = ""


class MathAgent(BaseAgent):
    """
    Specialized agent for mathematics tutoring.
    
    Features:
    - Solve math problems step-by-step
    - Extract formulas from documents
    - Generate practice problems
    - Explain mathematical concepts
    - Use Socratic method for teaching
    
    Usage:
        agent = MathAgent()
        result = await agent.execute(
            problem="Solve: x^2 + 2x + 1 = 0",
            task="solve",
            level="high_school"
        )
    """
    
    name = "math_agent"
    version = "1.0.0"
    description = "Chuyên gia toán học - Giải đề, công thức, hướng dẫn từng bước"
    icon = "📐"
    author = "AetherTutor"
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._topics = [
            "algebra", "geometry", "calculus", "statistics", "probability",
            "linear_algebra", "discrete_math", "number_theory", "trigonometry"
        ]
        self._levels = [
            "elementary", "middle_school", "high_school", 
            "undergraduate", "graduate"
        ]
    
    def _default_system_prompt(self) -> str:
        return """Bạn là Math Agent - chuyên gia dạy toán.

NHIỆM VỤ:
1. Giải bài toán từng bước với lời giải thích rõ ràng
2. Trích xuất công thức từ tài liệu
3. Tạo bài tập thực hành
4. Giải thích khái niệm toán học
5. Sử dụng phương pháp Socratic để hướng dẫn

QUY TẮC:
- LUÔN giải thích mỗi bước, không bỏ qua bước nào
- Sử dụng LaTeX cho công thức toán học
- Khuyến khích học sinh tự nghĩ, không chỉ đưa đáp án
- Đưa ra hints khi học sinh gặp khó khăn
- Kiểm tra lại kết quả cuối cùng

ĐỊNH DẠNG TRẢ VỀ:
Luôn trả về JSON với cấu trúc:
{
  "problem": "Bài toán ban đầu",
  "solution_steps": [{"step_number", "description", "formula", "explanation"}],
  "formulas": [{"name", "latex", "variables", "context"}],
  "hints": ["Gợi ý 1", "Gợi ý 2"],
  "explanation": "Giải thích tổng quát",
  "difficulty": "easy/medium/hard",
  "topic": "Chủ đề toán học"
}

LATEX FORMAT:
- Inline: $formula$
- Display: $$formula$$
- Ví dụ: $x = \\frac{-b \\pm \\sqrt{b^2 - 4ac}}{2a}$"""
    
    def get_capabilities(self) -> List[AgentCapabilities]:
        return [
            AgentCapabilities.MATH_TUTORING,
            AgentCapabilities.STEP_BY_STEP_SOLUTION,
            AgentCapabilities.QUIZ_GENERATION,
        ]
    
    async def execute(self, **kwargs) -> Dict[str, Any]:
        """
        Execute math tutoring task.
        
        Args:
            problem: Math problem to solve
            task: Task type (solve, explain, practice, extract_formulas, concept)
            level: Difficulty level (elementary, middle_school, high_school, undergraduate, graduate)
            topic: Math topic (algebra, calculus, geometry, etc.)
            document_text: Document text to extract formulas from
            
        Returns:
            Dict with math solution/result
        """
        problem = kwargs.get("problem", "")
        task = kwargs.get("task", "solve")
        level = kwargs.get("level", "high_school")
        topic = kwargs.get("topic", "")
        document_text = kwargs.get("document_text", "")
        
        if not problem and not document_text:
            return {"error": "No problem or document text provided", "status": "failed"}
        
        if level not in self._levels:
            return {
                "error": f"Invalid level: {level}",
                "valid_levels": self._levels,
                "status": "failed"
            }
        
        # Build prompt based on task
        prompt = self._build_prompt(problem, document_text, task, level, topic)
        
        try:
            # Call LLM with structured extraction
            result = await self._call_llm_structured(
                prompt=prompt,
                response_model=MathResponse,
                max_retries=2,
            )
            
            if result:
                return {
                    "status": "success",
                    "task": task,
                    "level": level,
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
                    "level": level,
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
        problem: str,
        document_text: str,
        task: str,
        level: str,
        topic: str
    ) -> str:
        """Build task-specific prompt."""
        
        prompts = {
            "solve": f"""Giải bài toán sau từng bước với lời giải thích chi tiết.

Mức độ: {level}
{f"Chủ đề: {topic}" if topic else ""}

Bài toán:
{problem}

Yêu cầu:
1. Phân tích đề bài
2. Giải từng bước (không bỏ qua bước nào)
3. Sử dụng LaTeX cho công thức
4. Kiểm tra lại kết quả
5. Đưa ra 2-3 hints để học sinh tự làm""",
            
            "explain": f"""Giải thích khái niệm/toán đề sau.

Mức độ: {level}
{f"Chủ đề: {topic}" if topic else ""}

Nội dung:
{problem}

Yêu cầu:
1. Giải thích từ cơ bản đến nâng cao
2. Đưa ra ví dụ minh họa
3. Sử dụng LaTeX cho công thức
4. Liên hệ với kiến thức liên quan""",
            
            "practice": f"""Tạo 5 bài tập thực hành về chủ đề sau.

Mức độ: {level}
{f"Chủ đề: {topic}" if topic else ""}

Nội dung tham khảo:
{problem}

Yêu cầu:
1. 5 bài tập từ dễ đến khó
2. Có đáp án và lời giải chi tiết
3. Sử dụng LaTeX cho công thức
4. Đưa ra hints cho mỗi bài""",
            
            "extract_formulas": f"""Trích xuất tất cả công thức toán học từ tài liệu sau.

Mức độ: {level}
{f"Chủ đề: {topic}" if topic else ""}

Tài liệu:
{document_text}

Yêu cầu:
1. Liệt kê tất cả công thức
2. Đặt tên cho mỗi công thức
3. Giải thích các biến số
4. Ngữ cảnh sử dụng""",
            
            "concept": f"""Giải thích khái niệm toán học sau.

Mức độ: {level}
Khái niệm: {problem}

Yêu cầu:
1. Định nghĩa rõ ràng
2. Ví dụ minh họa
3. Công thức liên quan (LaTeX)
4. Ứng dụng thực tế
5. Bài tập đơn giản để kiểm tra hiểu biết""",
        }
        
        return prompts.get(task, prompts["solve"])
