"""
MCP Extension for Agents - Standardized context sharing between agents.

Provides:
- AgentContext: Rich context for inter-agent communication
- Context sharing: user progress, graph entities, session state
- Standardized format for agent-to-agent data exchange
"""

from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field
from datetime import datetime


class AgentContext(BaseModel):
    """
    Rich context for inter-agent communication via MCP.
    
    This extends the basic MCPContext to include:
    - User learning progress
    - Active graph entities
    - Session state
    - Cross-agent shared data
    
    Usage:
        context = AgentContext(
            user_id="user123",
            session_id="session456",
            learning_progress={"topics": [...]},
            active_entities=["Class:Foo", "Function:bar"],
            session_state={"current_topic": "python"},
            shared_data={"key": "value"}
        )
    """
    
    user_id: str = Field(..., description="User identifier")
    session_id: str = Field(..., description="Session identifier")
    
    # Learning progress
    learning_progress: Dict[str, Any] = Field(
        default_factory=dict,
        description="User's learning progress (topics, mastery levels, etc.)"
    )
    
    # Active graph entities from current session
    active_entities: List[str] = Field(
        default_factory=list,
        description="List of entity names currently in focus"
    )
    
    # Session state
    session_state: Dict[str, Any] = Field(
        default_factory=dict,
        description="Current session state (topic, mode, preferences)"
    )
    
    # Cross-agent shared data
    shared_data: Dict[str, Any] = Field(
        default_factory=dict,
        description="Data shared between agents"
    )
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    def update_progress(self, key: str, value: Any) -> None:
        """Update learning progress."""
        self.learning_progress[key] = value
        self.updated_at = datetime.utcnow()
    
    def update_session_state(self, key: str, value: Any) -> None:
        """Update session state."""
        self.session_state[key] = value
        self.updated_at = datetime.utcnow()
    
    def share_data(self, agent_name: str, data: Any) -> None:
        """Share data with another agent."""
        if "agent_shares" not in self.shared_data:
            self.shared_data["agent_shares"] = {}
        
        if agent_name not in self.shared_data["agent_shares"]:
            self.shared_data["agent_shares"][agent_name] = []
        
        self.shared_data["agent_shares"][agent_name].append({
            "data": data,
            "timestamp": datetime.utcnow().isoformat()
        })
        self.updated_at = datetime.utcnow()
    
    def get_agent_data(self, agent_name: str) -> List[Dict]:
        """Get data shared by a specific agent."""
        return self.shared_data.get("agent_shares", {}).get(agent_name, [])
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict for MCP transmission."""
        return self.model_dump()
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AgentContext":
        """Create AgentContext from dict."""
        return cls(**data)


class ContextBuilder:
    """
    Helper class to build AgentContext from various data sources.
    
    Usage:
        builder = ContextBuilder()
        builder.set_user("user123", "session456")
        builder.add_learning_progress("python", {"mastery": 0.7})
        builder.add_active_entity("Class:MyClass")
        context = builder.build()
    """
    
    def __init__(self):
        self._user_id: Optional[str] = None
        self._session_id: Optional[str] = None
        self._learning_progress: Dict[str, Any] = {}
        self._active_entities: List[str] = []
        self._session_state: Dict[str, Any] = {}
        self._shared_data: Dict[str, Any] = {}
    
    def set_user(self, user_id: str, session_id: str) -> "ContextBuilder":
        """Set user and session."""
        self._user_id = user_id
        self._session_id = session_id
        return self
    
    def add_learning_progress(self, topic: str, data: Any) -> "ContextBuilder":
        """Add learning progress for a topic."""
        self._learning_progress[topic] = data
        return self
    
    def add_active_entity(self, entity_name: str) -> "ContextBuilder":
        """Add an active entity to focus list."""
        self._active_entities.append(entity_name)
        return self
    
    def add_active_entities(self, entity_names: List[str]) -> "ContextBuilder":
        """Add multiple active entities."""
        self._active_entities.extend(entity_names)
        return self
    
    def set_session_state(self, key: str, value: Any) -> "ContextBuilder":
        """Set session state value."""
        self._session_state[key] = value
        return self
    
    def add_shared_data(self, key: str, value: Any) -> "ContextBuilder":
        """Add shared data."""
        self._shared_data[key] = value
        return self
    
    def build(self) -> AgentContext:
        """Build the AgentContext."""
        if not self._user_id or not self._session_id:
            raise ValueError("user_id and session_id are required")
        
        return AgentContext(
            user_id=self._user_id,
            session_id=self._session_id,
            learning_progress=self._learning_progress,
            active_entities=self._active_entities,
            session_state=self._session_state,
            shared_data=self._shared_data,
        )
