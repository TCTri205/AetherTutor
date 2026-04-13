"""
Agent Registry - Dynamic agent discovery and registration.

Provides:
- Register/unregister agents
- List available agents
- Get agent by name/ID
- Version compatibility checking
"""

from typing import Dict, Optional, List
import logging
from .base_agent import BaseAgent

logger = logging.getLogger(__name__)


class AgentRegistry:
    """
    Registry for managing AI agents.
    
    Usage:
        registry = AgentRegistry()
        registry.register(my_agent)
        agent = registry.get("language_agent")
        agents = registry.list_agents()
    """
    
    def __init__(self):
        self._agents: Dict[str, BaseAgent] = {}
        self._metadata: Dict[str, Dict] = {}
    
    def register(
        self, 
        agent: BaseAgent, 
        agent_id: Optional[str] = None,
        enabled: bool = True,
        metadata: Optional[Dict] = None
    ) -> str:
        """
        Register an agent instance.
        
        Args:
            agent: Agent instance to register
            agent_id: Custom ID (defaults to agent.name)
            enabled: Whether agent is enabled
            metadata: Additional metadata
            
        Returns:
            Agent ID
        """
        aid = agent_id or agent.name
        
        if aid in self._agents:
            logger.warning(f"Agent {aid} already registered, overwriting")
        
        self._agents[aid] = agent
        self._metadata[aid] = {
            "enabled": enabled,
            "metadata": metadata or {},
        }
        
        logger.info(f"Registered agent: {aid} ({agent.name} v{agent.version})")
        return aid
    
    def unregister(self, agent_id: str) -> bool:
        """
        Unregister an agent.
        
        Args:
            agent_id: Agent ID to remove
            
        Returns:
            True if unregistered
        """
        if agent_id in self._agents:
            del self._agents[agent_id]
            del self._metadata[agent_id]
            logger.info(f"Unregistered agent: {agent_id}")
            return True
        return False
    
    def get(self, agent_id: str) -> Optional[BaseAgent]:
        """
        Get agent by ID.
        
        Args:
            agent_id: Agent identifier
            
        Returns:
            Agent instance or None
        """
        agent = self._agents.get(agent_id)
        
        if agent and not self._metadata.get(agent_id, {}).get("enabled", True):
            logger.warning(f"Agent {agent_id} is disabled")
            return None
        
        return agent
    
    def list_agents(self, enabled_only: bool = True) -> List[Dict]:
        """
        List all registered agents with info.
        
        Args:
            enabled_only: Only return enabled agents
            
        Returns:
            List of agent info dicts
        """
        result = []
        
        for aid, agent in self._agents.items():
            meta = self._metadata.get(aid, {})
            
            if enabled_only and not meta.get("enabled", True):
                continue
            
            info = agent.get_info()
            info["id"] = aid
            info["enabled"] = meta.get("enabled", True)
            result.append(info)
        
        return result
    
    def get_by_capability(self, capability: str) -> List[BaseAgent]:
        """
        Get agents that have a specific capability.
        
        Args:
            capability: Capability string (e.g., "language_learning")
            
        Returns:
            List of agents with the capability
        """
        result = []
        
        for aid, agent in self._agents.items():
            meta = self._metadata.get(aid, {})
            if not meta.get("enabled", True):
                continue
            
            caps = [c.value for c in agent.get_capabilities()]
            if capability in caps:
                result.append(agent)
        
        return result
    
    def is_registered(self, agent_id: str) -> bool:
        """Check if agent is registered."""
        return agent_id in self._agents
    
    def is_compatible(self, agent_id: str, required_version: str = "1.0.0") -> bool:
        """
        Check agent version compatibility.
        
        Args:
            agent_id: Agent identifier
            required_version: Minimum required version
            
        Returns:
            True if compatible
        """
        agent = self.get(agent_id)
        if not agent:
            return False
        
        # Simple semver comparison (major.minor)
        try:
            agent_major, agent_minor = map(int, agent.version.split(".")[:2])
            req_major, req_minor = map(int, required_version.split(".")[:2])
            
            if agent_major > req_major:
                return True
            if agent_major == req_major and agent_minor >= req_minor:
                return True
            
            return False
        except (ValueError, AttributeError):
            logger.warning(f"Invalid version format for agent {agent_id}")
            return False
    
    def enable(self, agent_id: str) -> bool:
        """Enable an agent."""
        if agent_id in self._metadata:
            self._metadata[agent_id]["enabled"] = True
            logger.info(f"Enabled agent: {agent_id}")
            return True
        return False
    
    def disable(self, agent_id: str) -> bool:
        """Disable an agent."""
        if agent_id in self._metadata:
            self._metadata[agent_id]["enabled"] = False
            logger.info(f"Disabled agent: {agent_id}")
            return True
        return False
    
    def count(self) -> int:
        """Return number of registered agents."""
        return len(self._agents)
    
    def clear(self) -> None:
        """Unregister all agents."""
        self._agents.clear()
        self._metadata.clear()
        logger.info("Cleared agent registry")


# Singleton instance
agent_registry = AgentRegistry()
