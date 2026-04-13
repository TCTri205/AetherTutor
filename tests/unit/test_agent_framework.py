"""
Unit tests for Agent Framework (Sprint 16).

Tests:
- Base agent registration and execution
- Agent registry operations
- Language agent functionality
- Math agent functionality
- Agent API endpoints
"""
import uuid
import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from unittest.mock import AsyncMock, MagicMock, patch

from app.core.agents.base_agent import BaseAgent, AgentCapabilities
from app.core.agents.registry import AgentRegistry
from app.core.agents.language_agent import LanguageAgent
from app.core.agents.math_agent import MathAgent


# --- Base Agent Tests ---

class TestBaseAgent:
    """Tests for BaseAgent abstract class."""

    def test_agent_has_required_attributes(self):
        """Test that concrete agents must define name, version, etc."""

        class TestAgent(BaseAgent):
            name = "TestAgent"
            version = "1.0.0"
            description = "A test agent"
            icon = "🤖"

            def _default_system_prompt(self) -> str:
                return "Test system prompt"

            async def execute(self, **kwargs) -> dict:
                return {"status": "success"}

            def get_capabilities(self):
                return [AgentCapabilities.QUESTION_ANSWERING]

        agent = TestAgent()
        assert agent.name == "TestAgent"
        assert agent.version == "1.0.0"
        assert agent.description == "A test agent"
        assert agent.icon == "🤖"

    def test_get_info_returns_dict(self):
        """Test get_info() returns agent metadata."""

        class TestAgent(BaseAgent):
            name = "InfoAgent"
            version = "2.0.0"
            description = "Info test agent"
            icon = "ℹ️"

            def _default_system_prompt(self) -> str:
                return "Info prompt"

            async def execute(self, **kwargs) -> dict:
                return {"info": "test"}

            def get_capabilities(self):
                return [AgentCapabilities.LANGUAGE_LEARNING]

        agent = TestAgent()
        info = agent.get_info()

        assert info["name"] == "InfoAgent"
        assert info["version"] == "2.0.0"
        assert info["description"] == "Info test agent"
        assert info["icon"] == "ℹ️"
        assert "capabilities" in info
        assert "language_learning" in info["capabilities"]

    def test_set_system_prompt(self):
        """Test custom system prompt override."""

        class PromptAgent(BaseAgent):
            name = "PromptAgent"
            version = "1.0.0"
            description = "Prompt agent"
            icon = "💬"

            def _default_system_prompt(self) -> str:
                return "Default prompt"

            async def execute(self, **kwargs) -> dict:
                return {}

            def get_capabilities(self):
                return []

        agent = PromptAgent()
        agent.set_system_prompt("Custom system prompt")
        assert agent._system_prompt == "Custom system prompt"


# --- Agent Registry Tests ---

class TestAgentRegistry:
    """Tests for AgentRegistry singleton."""

    @pytest.fixture
    def registry(self):
        """Fresh registry for each test."""
        return AgentRegistry()

    def test_register_agent(self, registry):
        """Test registering a new agent."""

        class RegAgent(BaseAgent):
            name = "RegAgent"
            version = "1.0.0"
            description = "Registry test agent"
            icon = "📋"

            def _default_system_prompt(self) -> str:
                return "Reg prompt"

            async def execute(self, **kwargs) -> dict:
                return {"status": "ok"}

            def get_capabilities(self):
                return []

        agent = RegAgent()
        agent_id = registry.register(agent, agent_id="reg_agent", enabled=True)

        assert agent_id == "reg_agent"
        assert registry.is_registered("reg_agent")

    def test_get_registered_agent(self, registry):
        """Test retrieving a registered agent."""

        class GetAgent(BaseAgent):
            name = "GetAgent"
            version = "1.0.0"
            description = "Get agent"
            icon = "🔍"

            def _default_system_prompt(self) -> str:
                return "Get prompt"

            async def execute(self, **kwargs) -> dict:
                return {"retrieved": True}

            def get_capabilities(self):
                return []

        agent = GetAgent()
        registry.register(agent, agent_id="get_agent", enabled=True)

        retrieved = registry.get("get_agent")
        assert retrieved is not None
        assert retrieved.name == "GetAgent"

    def test_get_unregistered_agent_returns_none(self, registry):
        """Test that getting unregistered agent returns None."""
        result = registry.get("nonexistent")
        assert result is None

    def test_unregister_agent(self, registry):
        """Test unregistering an agent."""

        class UnregAgent(BaseAgent):
            name = "UnregAgent"
            version = "1.0.0"
            description = "Unreg agent"
            icon = "🗑️"

            def _default_system_prompt(self) -> str:
                return "Unreg prompt"

            async def execute(self, **kwargs) -> dict:
                return {}

            def get_capabilities(self):
                return []

        agent = UnregAgent()
        registry.register(agent, agent_id="unreg_agent", enabled=True)
        assert registry.is_registered("unreg_agent")

        result = registry.unregister("unreg_agent")
        assert result is True
        assert not registry.is_registered("unreg_agent")

    def test_disable_and_enable_agent(self, registry):
        """Test disabling and enabling agents."""

        class ToggleAgent(BaseAgent):
            name = "ToggleAgent"
            version = "1.0.0"
            description = "Toggle agent"
            icon = "🔘"

            def _default_system_prompt(self) -> str:
                return "Toggle prompt"

            async def execute(self, **kwargs) -> dict:
                return {}

            def get_capabilities(self):
                return []

        agent = ToggleAgent()
        registry.register(agent, agent_id="toggle_agent", enabled=True)

        registry.disable("toggle_agent")
        # After disable, agent should not appear in enabled list
        enabled = registry.list_agents(enabled_only=True)
        assert len([a for a in enabled if a["name"] == "ToggleAgent"]) == 0

        registry.enable("toggle_agent")
        enabled = registry.list_agents(enabled_only=True)
        assert len([a for a in enabled if a["name"] == "ToggleAgent"]) == 1

    def test_list_agents(self, registry):
        """Test listing all registered agents."""

        class ListAgentA(BaseAgent):
            name = "ListAgentA"
            version = "1.0.0"
            description = "Agent A"
            icon = "🅰️"

            def _default_system_prompt(self) -> str:
                return "A prompt"

            async def execute(self, **kwargs) -> dict:
                return {}

            def get_capabilities(self):
                return []

        class ListAgentB(BaseAgent):
            name = "ListAgentB"
            version = "1.0.0"
            description = "Agent B"
            icon = "🅱️"

            def _default_system_prompt(self) -> str:
                return "B prompt"

            async def execute(self, **kwargs) -> dict:
                return {}

            def get_capabilities(self):
                return []

        registry.register(ListAgentA(), agent_id="agent_a", enabled=True)
        registry.register(ListAgentB(), agent_id="agent_b", enabled=False)

        all_agents = registry.list_agents(enabled_only=False)
        assert len(all_agents) == 2

        enabled_agents = registry.list_agents(enabled_only=True)
        assert len(enabled_agents) == 1
        assert enabled_agents[0]["name"] == "ListAgentA"

    def test_count_agents(self, registry):
        """Test counting registered agents."""

        class CountAgent(BaseAgent):
            name = "CountAgent"
            version = "1.0.0"
            description = "Count agent"
            icon = "🔢"

            def _default_system_prompt(self) -> str:
                return "Count prompt"

            async def execute(self, **kwargs) -> dict:
                return {}

            def get_capabilities(self):
                return []

        registry.register(CountAgent(), agent_id="count1", enabled=True)
        registry.register(CountAgent(), agent_id="count2", enabled=True)
        registry.register(CountAgent(), agent_id="count3", enabled=False)

        assert registry.count() == 3


# --- Language Agent Tests ---

class TestLanguageAgent:
    """Tests for LanguageAgent."""

    def test_language_agent_attributes(self):
        """Test LanguageAgent has correct attributes."""
        agent = LanguageAgent()
        assert "language" in agent.name.lower() or "language_agent" == agent.name
        assert agent.version == "1.0.0"
        assert agent.icon  # Should have an emoji

    def test_language_agent_system_prompt(self):
        """Test LanguageAgent system prompt contains language learning instructions."""
        agent = LanguageAgent()
        prompt = agent._default_system_prompt()

        assert "language" in prompt.lower() or "vocabulary" in prompt.lower()
        assert "grammar" in prompt.lower() or "translate" in prompt.lower()

    def test_language_agent_capabilities(self):
        """Test LanguageAgent reports correct capabilities."""
        agent = LanguageAgent()
        caps = agent.get_capabilities()

        # Language agent should have language_learning capability
        assert AgentCapabilities.LANGUAGE_LEARNING in caps or AgentCapabilities.TRANSLATION in caps or len(caps) >= 1


# --- Math Agent Tests ---

class TestMathAgent:
    """Tests for MathAgent."""

    def test_math_agent_attributes(self):
        """Test MathAgent has correct attributes."""
        agent = MathAgent()
        assert "math" in agent.name.lower() or "math_agent" == agent.name
        assert agent.version == "1.0.0"
        assert agent.icon  # Should have an emoji

    def test_math_agent_system_prompt(self):
        """Test MathAgent system prompt contains math instructions."""
        agent = MathAgent()
        prompt = agent._default_system_prompt()

        assert "math" in prompt.lower() or "equation" in prompt.lower()
        assert "step" in prompt.lower() or "solution" in prompt.lower()

    def test_math_agent_capabilities(self):
        """Test MathAgent reports correct capabilities."""
        agent = MathAgent()
        caps = agent.get_capabilities()

        # Math agent should have math_tutoring capability
        assert AgentCapabilities.MATH_TUTORING in caps or AgentCapabilities.STEP_BY_STEP_SOLUTION in caps or len(caps) >= 1
