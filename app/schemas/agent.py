"""
Agent Schemas - Pydantic models for agent configuration and API.
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class AgentConfig(BaseModel):
    """Agent configuration schema."""
    id: str = Field(..., description="Unique agent identifier")
    name: str = Field(..., description="Agent display name")
    description: str = Field(default="", description="Agent description")
    icon: str = Field(default="🤖", description="Agent emoji icon")
    version: str = Field(default="1.0.0", description="Agent version")
    system_prompt_template: str = Field(..., description="System prompt template")
    capabilities: List[str] = Field(default_factory=list, description="Agent capabilities")
    custom_config: Dict[str, Any] = Field(default_factory=dict, description="Custom agent config")
    enabled: bool = Field(default=True, description="Whether agent is enabled")


class AgentInfo(BaseModel):
    """Agent information for API responses."""
    id: str
    name: str
    description: str
    icon: str
    version: str
    capabilities: List[str]
    enabled: bool
    author: str = "AetherTutor"


class AgentListResponse(BaseModel):
    """Response for listing agents."""
    agents: List[AgentInfo]
    total: int


class AgentCreateRequest(BaseModel):
    """Request to create/register a custom agent."""
    name: str = Field(..., min_length=1, max_length=100)
    description: str = Field(default="", max_length=500)
    icon: str = Field(default="🤖", max_length=10)
    system_prompt_template: str = Field(..., min_length=10)
    capabilities: List[str] = Field(default_factory=list)
    custom_config: Dict[str, Any] = Field(default_factory=dict)


class AgentUpdateRequest(BaseModel):
    """Request to update agent configuration."""
    description: Optional[str] = None
    icon: Optional[str] = None
    system_prompt_template: Optional[str] = None
    capabilities: Optional[List[str]] = None
    custom_config: Optional[Dict[str, Any]] = None
    enabled: Optional[bool] = None
