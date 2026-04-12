"""
Agent Marketplace Infrastructure - Schemas and utilities for agent template export/import.

Note: Community sharing feature reserved for future release.
Current implementation supports local export/import only.
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime


class AgentTemplate(BaseModel):
    """
    Exportable agent configuration template.
    
    Can be exported to JSON and imported back to recreate agent.
    Used for:
    - Backing up agent configurations
    - Sharing configurations between environments
    - Future community marketplace
    """
    template_id: str = Field(..., description="Unique template identifier")
    agent_name: str = Field(..., description="Agent name")
    agent_version: str = Field(default="1.0.0", description="Agent version")
    description: str = Field(default="", description="Template description")
    author: str = Field(default="Anonymous", description="Template author")
    
    # Agent configuration
    system_prompt_template: str = Field(..., description="System prompt")
    capabilities: List[str] = Field(default_factory=list, description="Agent capabilities")
    custom_config: Dict[str, Any] = Field(default_factory=dict, description="Custom config")
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    tags: List[str] = Field(default_factory=list, description="Search tags")
    icon: str = Field(default="🤖", description="Agent emoji icon")
    
    def to_export_dict(self) -> Dict[str, Any]:
        """Convert to export-friendly dict (excludes internal IDs)."""
        return {
            "template_id": self.template_id,
            "agent_name": self.agent_name,
            "agent_version": self.agent_version,
            "description": self.description,
            "author": self.author,
            "system_prompt_template": self.system_prompt_template,
            "capabilities": self.capabilities,
            "custom_config": self.custom_config,
            "created_at": self.created_at.isoformat(),
            "tags": self.tags,
            "icon": self.icon,
        }
    
    @classmethod
    def from_import_dict(cls, data: Dict[str, Any]) -> "AgentTemplate":
        """Create template from imported data."""
        return cls(**data)


class AgentTemplateList(BaseModel):
    """Response for listing agent templates."""
    templates: List[AgentTemplate]
    total: int


class MarketplaceListing(BaseModel):
    """
    Future: Community marketplace listing.
    
    Reserved for v1.0.0 release.
    """
    template_id: str
    agent_name: str
    description: str
    author: str
    downloads: int = 0
    rating: float = 0.0
    tags: List[str] = []
    icon: str = "🤖"
    created_at: datetime = Field(default_factory=datetime.utcnow)


# Placeholder endpoint for future marketplace
from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/agents/templates", tags=["agent-templates"])


@router.get("")
async def list_agent_templates():
    """
    List available agent templates.
    
    Currently returns empty list.
    Community marketplace coming in v1.0.0.
    """
    return {
        "templates": [],
        "total": 0,
        "message": "Agent template marketplace coming soon in v1.0.0"
    }


@router.post("/import")
async def import_agent_template(template_data: Dict[str, Any]):
    """
    Import an agent template from JSON.
    
    Creates a new agent instance from the template configuration.
    """
    try:
        template = AgentTemplate.from_import_dict(template_data)
        
        # Create agent from template
        from app.core.agents.base_agent import BaseAgent, AgentCapabilities
        
        class ImportedAgent(BaseAgent):
            name = template.agent_name
            version = template.agent_version
            description = template.description
            icon = template.icon
            
            def _default_system_prompt(self) -> str:
                return template.system_prompt_template
            
            async def execute(self, **kwargs) -> dict:
                return {"status": "success", "message": "Imported agent executed"}
            
            def get_capabilities(self):
                caps = []
                for cap_str in template.capabilities:
                    try:
                        caps.append(AgentCapabilities(cap_str))
                    except ValueError:
                        pass
                return caps
        
        agent = ImportedAgent(custom_config=template.custom_config)
        
        from app.core.agents.registry import agent_registry
        agent_id = agent_registry.register(
            agent,
            agent_id=f"imported_{template.agent_name}",
            enabled=True,
            metadata={"imported": True, "template_id": template.template_id}
        )
        
        return {
            "status": "success",
            "agent_id": agent_id,
            "message": f"Agent template '{template.agent_name}' imported successfully"
        }
    
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Failed to import agent template: {str(e)}"
        )


@router.post("/export/{agent_id}")
async def export_agent_template(agent_id: str):
    """
    Export an agent configuration as a template.
    
    Returns JSON that can be imported later or shared.
    """
    from app.core.agents.registry import agent_registry
    
    agent = agent_registry.get(agent_id)
    
    if not agent:
        raise HTTPException(
            status_code=404,
            detail=f"Agent '{agent_id}' not found"
        )
    
    import uuid
    from datetime import datetime
    
    template = AgentTemplate(
        template_id=f"template_{uuid.uuid4().hex[:8]}",
        agent_name=agent.name,
        agent_version=agent.version,
        description=agent.description,
        author=agent.author,
        system_prompt_template=agent._system_prompt or "",
        capabilities=[c.value for c in agent.get_capabilities()],
        custom_config=agent._config,
        icon=agent.icon,
        tags=[agent.name, agent.version],
    )
    
    return {
        "status": "success",
        "template": template.to_export_dict(),
        "message": f"Agent '{agent_id}' exported as template"
    }
