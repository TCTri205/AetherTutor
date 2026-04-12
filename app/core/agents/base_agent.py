"""
Base Agent Class - Abstract base for all AI agents in AetherTutor.

Provides:
- Standardized LLM access
- System prompt management
- Structured output support
- Capability declarations
- MCP context integration
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from enum import Enum
import logging

from app.services.llm_service import llm_service
from app.mcp.skeleton import MCPContext, mcp_skeleton

logger = logging.getLogger(__name__)


class AgentCapabilities(str, Enum):
    """Agent capability flags for registration."""
    QUIZ_GENERATION = "quiz_generation"
    FLASHCARD_CREATION = "flashcard_creation"
    CODE_ANALYSIS = "code_analysis"
    LANGUAGE_LEARNING = "language_learning"
    MATH_TUTORING = "math_tutoring"
    GRAPH_VISUALIZATION = "graph_visualization"
    EXAM_PREPARATION = "exam_preparation"
    TRANSLATION = "translation"
    GRAMMAR_CHECK = "grammar_check"
    STEP_BY_STEP_SOLUTION = "step_by_step_solution"


class BaseAgent(ABC):
    """
    Abstract base class for all AI agents.
    
    All specialized agents must inherit from this class and implement:
    - _default_system_prompt()
    - execute()
    - get_capabilities()
    
    Usage:
        class MyAgent(BaseAgent):
            name = "my_agent"
            version = "1.0.0"
            
            def _default_system_prompt(self) -> str:
                return "You are..."
            
            async def execute(self, **kwargs) -> Dict[str, Any]:
                ...
            
            def get_capabilities(self) -> list[AgentCapabilities]:
                return [AgentCapabilities.QUIZ_GENERATION]
    """
    
    name: str = "base_agent"
    version: str = "1.0.0"
    description: str = ""
    icon: str = "🤖"  # Emoji for UI
    author: str = "AetherTutor"
    
    def __init__(self, system_prompt: Optional[str] = None, **kwargs):
        """
        Initialize agent.
        
        Args:
            system_prompt: Custom system prompt (overrides default)
            **kwargs: Additional agent-specific configuration
        """
        self._system_prompt = system_prompt or self._default_system_prompt()
        self._config = kwargs
        self._mcp_context: Optional[MCPContext] = None
        
        logger.info(f"Initialized agent: {self.name} v{self.version}")
    
    def _default_system_prompt(self) -> str:
        """Return default system prompt for this agent."""
        return f"You are {self.name}, a specialized AI agent in AetherTutor learning platform."
    
    def set_system_prompt(self, prompt: str) -> None:
        """Override system prompt."""
        self._system_prompt = prompt
    
    async def _call_llm(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> str:
        """
        Standard LLM chat completion call.
        
        Args:
            messages: Chat messages (without system prompt)
            temperature: Sampling temperature
            max_tokens: Max response tokens
            **kwargs: Additional LLM parameters
            
        Returns:
            Response text
        """
        full_messages = [
            {"role": "system", "content": self._system_prompt},
            *messages
        ]
        
        response = await llm_service.get_chat_completion(
            full_messages,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs
        )
        
        return response
    
    async def _call_llm_structured(
        self,
        prompt: str,
        response_model: type,
        max_retries: int = 3,
        temperature: float = 0.7,
    ) -> Optional[Any]:
        """
        LLM call with structured Pydantic output.
        
        Args:
            prompt: User prompt
            response_model: Pydantic model for structured output
            max_retries: Retry attempts
            temperature: Sampling temperature
            
        Returns:
            Parsed Pydantic model or None
        """
        return await llm_service.structured_extraction(
            prompt=prompt,
            response_model=response_model,
            max_retries=max_retries,
            temperature=temperature,
        )
    
    async def _call_llm_stream(
        self,
        messages: List[Dict[str, str]],
        **kwargs
    ):
        """
        Streaming LLM response.
        
        Args:
            messages: Chat messages
            **kwargs: Additional LLM parameters
            
        Yields:
            Response chunks
        """
        full_messages = [
            {"role": "system", "content": self._system_prompt},
            *messages
        ]
        
        async for chunk in llm_service.stream_chat_completion(full_messages, **kwargs):
            yield chunk
    
    def get_capabilities(self) -> List[AgentCapabilities]:
        """
        Return list of agent capabilities.
        
        Override in subclass to declare specific capabilities.
        """
        return []
    
    def get_config_schema(self) -> Dict[str, Any]:
        """
        Return agent configuration schema.
        
        Override to provide custom config validation.
        """
        return {
            "name": self.name,
            "version": self.version,
            "capabilities": [c.value for c in self.get_capabilities()],
            "custom_config": self._config
        }
    
    def set_mcp_context(self, session_id: str) -> None:
        """
        Set MCP context for inter-agent communication.
        
        Args:
            session_id: Session identifier for context lookup
        """
        self._mcp_context = mcp_skeleton.get_context(session_id)
    
    def get_mcp_context(self) -> Optional[MCPContext]:
        """Get current MCP context."""
        return self._mcp_context
    
    def update_mcp_context(self, key: str, value: Any) -> None:
        """
        Update value in MCP context metadata.
        
        Args:
            key: Metadata key
            value: Metadata value
        """
        if self._mcp_context:
            self._mcp_context.metadata[key] = value
    
    @abstractmethod
    async def execute(self, **kwargs) -> Dict[str, Any]:
        """
        Main entry point for agent execution.
        
        Must be implemented by subclass.
        
        Args:
            **kwargs: Agent-specific input parameters
            
        Returns:
            Dict with execution result
        """
        ...
    
    def get_info(self) -> Dict[str, Any]:
        """Return agent information for registry/UI."""
        return {
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "icon": self.icon,
            "author": self.author,
            "capabilities": [c.value for c in self.get_capabilities()],
            "config_schema": self.get_config_schema(),
        }
    
    async def health_check(self) -> bool:
        """
        Check if agent is healthy.
        
        Override for custom health checks.
        """
        return True
