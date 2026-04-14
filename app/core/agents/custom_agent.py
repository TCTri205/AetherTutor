"""
Custom Agent Factory - Factory pattern for dynamically configured agents.

Provides a reusable, module-level class that accepts runtime configuration
instead of creating new class definitions per request (which causes memory leak).
"""

from typing import Dict, Any, List, Optional

from app.core.agents.base_agent import BaseAgent, AgentCapabilities


class CustomAgent(BaseAgent):
    """
    Generic custom agent with configurable parameters.

    Instead of dynamically creating class definitions at runtime
    (which causes memory leak), use this factory class with
    runtime configuration.

    Example:
        agent = CustomAgent(
            name="my_agent",
            description="A custom agent",
            system_prompt="You are a helpful assistant...",
            capabilities=[AgentCapabilities.QUIZ_GENERATION],
            custom_config={"temperature": 0.7}
        )
    """

    def __init__(
        self,
        name: str,
        description: str,
        system_prompt: str,
        capabilities: List[AgentCapabilities],
        icon: str = "🤖",
        custom_config: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize custom agent.

        Args:
            name: Agent name (must be unique)
            description: Agent description
            system_prompt: System prompt for LLM
            capabilities: List of agent capabilities
            icon: Emoji icon for UI
            custom_config: Additional configuration
        """
        self._name = name
        self._description = description
        self._capabilities = capabilities
        self.icon = icon

        super().__init__(system_prompt=system_prompt, **(custom_config or {}))

    @property
    def name(self) -> str:
        """Agent name (overrides class attribute)."""
        return self._name

    @property
    def description(self) -> str:
        """Agent description (overrides class attribute)."""
        return self._description

    def _default_system_prompt(self) -> str:
        """Return configured system prompt."""
        # System prompt is already set in super().__init__
        # This method won't be called since we pass system_prompt explicitly
        return ""

    async def execute(self, **kwargs) -> Dict[str, Any]:
        """
        Execute agent with provided input.

        Args:
            **kwargs: Agent-specific input parameters

        Returns:
            Dict with execution result
        """
        # Default implementation: pass input to LLM
        messages = kwargs.get("messages", [])
        if not messages and kwargs.get("prompt"):
            messages = [{"role": "user", "content": kwargs["prompt"]}]

        if not messages:
            return {"status": "error", "message": "No input provided"}

        try:
            response = await self._call_llm(messages)
            return {
                "status": "success",
                "response": response,
                "agent_name": self._name,
            }
        except Exception as e:
            return {
                "status": "error",
                "message": str(e),
                "agent_name": self._name,
            }

    def get_capabilities(self) -> List[AgentCapabilities]:
        """Return configured capabilities."""
        return self._capabilities

    def get_config_schema(self) -> Dict[str, Any]:
        """Return agent configuration schema."""
        return {
            "name": self._name,
            "version": self.version,
            "capabilities": [c.value for c in self._capabilities],
            "custom_config": self._config,
        }
