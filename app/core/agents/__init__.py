"""
Agent module for AetherTutor.

Provides:
- BaseAgent: Abstract base class for all agents
- AgentRegistry: Dynamic agent discovery and registration
- Specialized agents: Language, Math, etc.
"""

from .base_agent import BaseAgent, AgentCapabilities
from .registry import agent_registry

__all__ = ["BaseAgent", "AgentCapabilities", "agent_registry"]
