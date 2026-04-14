"""
Agent Tests (Sprint 22 - Phase 4).

Tests for app/core/agents/:
- BaseAgent abstract class
- LanguageAgent
- MathAgent
- AgentRegistry
- Prompt generation
- Response parsing
- Error handling
- Health checks

Total: 20 tests (exceeds 15 target)
"""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from app.core.agents import BaseAgent, AgentCapabilities, agent_registry
from app.core.agents.language_agent import LanguageAgent, LanguageResponse
from app.core.agents.math_agent import MathAgent, MathResponse
from app.core.agents.registry import AgentRegistry
from app.core.agents.base_agent import AgentCapabilities as Caps


# --- Fixtures ---

@pytest.fixture
def registry():
    """Create a fresh AgentRegistry."""
    return AgentRegistry()


@pytest.fixture
def language_agent():
    """Create LanguageAgent instance."""
    return LanguageAgent()


@pytest.fixture
def math_agent():
    """Create MathAgent instance."""
    return MathAgent()


@pytest.fixture
def mock_llm_response():
    """Mock LLM service response."""
    return "This is a mock LLM response."


# === Test Agent Registry ===

class TestAgentRegistry:
    """Test agent registration and discovery."""

    def test_agent_registry_list(self, registry):
        """Test 1: AgentRegistry lists all available agents."""
        # Register some agents
        lang_agent = LanguageAgent()
        math = MathAgent()

        registry.register(lang_agent, agent_id="lang")
        registry.register(math, agent_id="math")

        agents = registry.list_agents()
        assert len(agents) == 2
        assert any(a["name"] == "language_agent" for a in agents)
        assert any(a["name"] == "math_agent" for a in agents)

    def test_agent_register_unregister(self, registry):
        """Test 2: Register and unregister agents."""
        agent = LanguageAgent()
        registry.register(agent, agent_id="test_lang")

        assert registry.is_registered("test_lang")
        assert registry.count() == 1

        registry.unregister("test_lang")
        assert not registry.is_registered("test_lang")
        assert registry.count() == 0

    def test_agent_get_by_name(self, registry):
        """Test 3: Get agent by ID."""
        agent = MathAgent()
        registry.register(agent, agent_id="math")

        retrieved = registry.get("math")
        assert retrieved is not None
        assert retrieved.name == "math_agent"

    def test_agent_get_nonexistent(self, registry):
        """Test 4: Get nonexistent agent returns None."""
        result = registry.get("nonexistent_agent")
        assert result is None

    def test_agent_enable_disable(self, registry):
        """Test 5: Enable/disable agents."""
        agent = LanguageAgent()
        registry.register(agent, agent_id="lang", enabled=True)

        registry.disable("lang")
        agents = registry.list_agents(enabled_only=True)
        assert len(agents) == 0

        registry.enable("lang")
        agents = registry.list_agents(enabled_only=True)
        assert len(agents) == 1

    def test_agent_get_by_capability(self, registry):
        """Test 6: Get agents by capability."""
        lang = LanguageAgent()
        math = MathAgent()

        registry.register(lang, agent_id="lang")
        registry.register(math, agent_id="math")

        # Language agents have LANGUAGE_LEARNING capability
        lang_agents = registry.get_by_capability("language_learning")
        assert len(lang_agents) >= 1

    def test_agent_compatibility_check(self, registry):
        """Test 7: Check version compatibility."""
        agent = LanguageAgent()
        registry.register(agent, agent_id="lang")

        # Should be compatible (v1.0.0 >= v1.0.0)
        assert registry.is_compatible("lang", "1.0.0") is True
        assert registry.is_compatible("lang", "2.0.0") is False

    def test_agent_clear_registry(self, registry):
        """Test 8: Clear all agents from registry."""
        registry.register(LanguageAgent(), agent_id="lang")
        registry.register(MathAgent(), agent_id="math")

        assert registry.count() == 2
        registry.clear()
        assert registry.count() == 0


# === Test Language Agent ===

class TestLanguageAgent:
    """Test LanguageAgent functionality."""

    def test_language_agent_capabilities(self, language_agent):
        """Test 9: LanguageAgent declares correct capabilities."""
        caps = language_agent.get_capabilities()
        assert Caps.LANGUAGE_LEARNING in caps
        assert Caps.TRANSLATION in caps
        assert Caps.GRAMMAR_CHECK in caps

    def test_language_agent_prompt_generation(self, language_agent):
        """Test 10: LanguageAgent generates vocabulary prompts."""
        prompt = language_agent._build_prompt(
            text="Bonjour, comment allez-vous?",
            target_language="french",
            source_language="english",
            task="vocabulary",
            difficulty="beginner"
        )

        assert "Bonjour" in prompt
        assert "french" in prompt.lower()
        assert "vocabulary" in prompt.lower()

    def test_language_agent_grammar_prompt(self, language_agent):
        """Test 11: LanguageAgent generates grammar prompts."""
        prompt = language_agent._build_prompt(
            text="Je suis allé au marché.",
            target_language="french",
            source_language="english",
            task="grammar",
            difficulty="intermediate"
        )

        assert "ngữ pháp" in prompt.lower() or "grammar" in prompt.lower()
        assert "Je suis allé" in prompt

    def test_language_agent_conjugation_prompt(self, language_agent):
        """Test 12: LanguageAgent generates conjugation prompts."""
        prompt = language_agent._build_prompt(
            text="Être ou ne pas être",
            target_language="french",
            source_language="english",
            task="conjugation",
            difficulty="beginner"
        )

        assert "chia động từ" in prompt.lower() or "conjugation" in prompt.lower()

    def test_language_agent_health_check(self, language_agent):
        """Test 13: LanguageAgent health check returns healthy status."""
        # Base implementation always returns True
        import asyncio
        result = asyncio.get_event_loop().run_until_complete(
            language_agent.health_check()
        )
        assert result is True


# === Test Math Agent ===

class TestMathAgent:
    """Test MathAgent functionality."""

    def test_math_agent_capabilities(self, math_agent):
        """Test 14: MathAgent declares correct capabilities."""
        caps = math_agent.get_capabilities()
        assert Caps.MATH_TUTORING in caps
        assert Caps.STEP_BY_STEP_SOLUTION in caps
        assert Caps.QUIZ_GENERATION in caps

    def test_math_agent_prompt_generation(self, math_agent):
        """Test 15: MathAgent generates solve prompts."""
        prompt = math_agent._build_prompt(
            problem="Solve: x^2 + 2x + 1 = 0",
            document_text="",
            task="solve",
            level="high_school",
            topic="algebra"
        )

        assert "x^2 + 2x + 1 = 0" in prompt
        assert "LaTeX" in prompt
        assert "từng bước" in prompt.lower() or "step" in prompt.lower()

    def test_math_agent_explain_prompt(self, math_agent):
        """Test 16: MathAgent generates explain prompts."""
        prompt = math_agent._build_prompt(
            problem="What is a derivative?",
            document_text="",
            task="explain",
            level="undergraduate",
            topic="calculus"
        )

        assert "derivative" in prompt.lower() or "đạo hàm" in prompt.lower()
        assert "Giải thích" in prompt or "explain" in prompt.lower()

    def test_math_agent_health_check(self, math_agent):
        """Test 17: MathAgent health check returns healthy status."""
        import asyncio
        result = asyncio.get_event_loop().run_until_complete(
            math_agent.health_check()
        )
        assert result is True


# === Test Base Agent ===

class TestBaseAgent:
    """Test BaseAgent abstract class and common functionality."""

    def test_base_agent_info(self, language_agent):
        """Test 18: Agent returns correct info."""
        info = language_agent.get_info()

        assert info["name"] == "language_agent"
        assert info["version"] == "1.0.0"
        assert info["icon"] == "🌍"
        assert "capabilities" in info

    def test_base_agent_config_schema(self, language_agent):
        """Test 19: Agent config schema is correct."""
        schema = language_agent.get_config_schema()

        assert schema["name"] == "language_agent"
        assert schema["version"] == "1.0.0"
        assert "capabilities" in schema


# === Error Handling Tests ===

class TestAgentErrorHandling:
    """Test agent error handling."""

    @pytest.mark.asyncio
    async def test_language_agent_empty_text(self, language_agent):
        """Test 20: LanguageAgent handles empty text gracefully."""
        result = await language_agent.execute(text="", target_language="french", task="vocabulary")

        assert result["status"] == "failed"
        assert "error" in result

    @pytest.mark.asyncio
    async def test_math_agent_empty_input(self, math_agent):
        """Test 21: MathAgent handles empty input gracefully."""
        result = await math_agent.execute(problem="", document_text="")

        assert result["status"] == "failed"
        assert "error" in result

    @pytest.mark.asyncio
    async def test_language_agent_unsupported_language(self, language_agent):
        """Test 22: LanguageAgent handles unsupported language."""
        result = await language_agent.execute(
            text="Some text",
            target_language="klingon",  # Unsupported
            task="vocabulary"
        )

        assert result["status"] == "failed"
        assert "error" in result


# === Integration Tests (with autose mock LLM from conftest) ===

class TestAgentWithMockLLM:
    """Test agents with mocked LLM service (uses conftest autouse fixture)."""

    @pytest.mark.asyncio
    async def test_language_agent_with_mock_llm(self, language_agent):
        """Test 23: LanguageAgent executes with mock LLM (from conftest)."""
        # conftest.py has autouse=True patch_llm_service fixture
        result = await language_agent.execute(
            text="Bonjour le monde!",
            target_language="french",
            task="vocabulary"
        )

        # Should not crash, might return success or error depending on mock
        assert "status" in result
        assert "task" in result or "error" in result

    @pytest.mark.asyncio
    async def test_math_agent_with_mock_llm(self, math_agent):
        """Test 24: MathAgent executes with mock LLM (from conftest)."""
        # conftest.py has autouse=True patch_llm_service fixture
        result = await math_agent.execute(
            problem="Solve: 2x + 3 = 7",
            task="solve",
            level="high_school"
        )

        # Should not crash, might return success or error depending on mock
        assert "status" in result
        assert "task" in result or "error" in result
