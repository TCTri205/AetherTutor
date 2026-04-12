"""
Agent Management API - Endpoints for managing AI agents.

Endpoints:
- GET /agents - List available agents
- GET /agents/{id} - Get agent details
- POST /agents - Register custom agent
- PUT /agents/{id} - Update agent config
- DELETE /agents/{id} - Unregister agent
- GET /agents/capabilities/{capability} - Get agents by capability
"""

from typing import List
from fastapi import APIRouter, HTTPException, Depends
from uuid import UUID
import logging

from app.schemas.agent import (
    AgentConfig, AgentInfo, AgentListResponse,
    AgentCreateRequest, AgentUpdateRequest
)
from app.core.agents.base_agent import BaseAgent, AgentCapabilities
from app.core.agents.registry import agent_registry
from app.core.agents.language_agent import LanguageAgent
from app.core.agents.math_agent import MathAgent
from app.dependencies import get_current_user
from app.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/agents", tags=["agents"])


def _auto_register_builtin_agents():
    """Auto-register built-in agents if not already registered."""
    if not agent_registry.is_registered("language_agent"):
        agent_registry.register(
            LanguageAgent(),
            agent_id="language_agent",
            enabled=True,
            metadata={"builtin": True}
        )
    
    if not agent_registry.is_registered("math_agent"):
        agent_registry.register(
            MathAgent(),
            agent_id="math_agent",
            enabled=True,
            metadata={"builtin": True}
        )


@router.on_event("startup")
async def startup_event():
    """Register built-in agents on startup."""
    _auto_register_builtin_agents()
    logger.info(f"Registered {agent_registry.count()} agents")


@router.get("", response_model=AgentListResponse)
async def list_agents(
    enabled_only: bool = True,
    current_user: User = Depends(get_current_user)
):
    """
    List all available agents.
    
    Returns agent information including name, description, capabilities,
    and configuration schema for UI rendering.
    """
    agents = agent_registry.list_agents(enabled_only=enabled_only)
    
    return AgentListResponse(
        agents=[AgentInfo(**a) for a in agents],
        total=len(agents)
    )


@router.get("/{agent_id}", response_model=AgentInfo)
async def get_agent(
    agent_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Get detailed information about a specific agent.
    
    Args:
        agent_id: Agent identifier
    """
    agent = agent_registry.get(agent_id)
    
    if not agent:
        raise HTTPException(
            status_code=404,
            detail=f"Agent '{agent_id}' not found"
        )
    
    info = agent.get_info()
    info["id"] = agent_id
    return AgentInfo(**info)


@router.post("", status_code=201)
async def register_agent(
    request: AgentCreateRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Register a custom agent.
    
    Creates a new agent instance with the provided configuration.
    The agent will be available immediately after registration.
    """
    # Check if agent already exists
    if agent_registry.is_registered(request.name):
        raise HTTPException(
            status_code=409,
            detail=f"Agent '{request.name}' already registered"
        )
    
    # Create a generic agent instance from config
    # Note: For custom agents, you'd typically have a factory or plugin system
    # For now, we'll create a placeholder agent
    try:
        from app.core.agents.base_agent import BaseAgent
        
        class CustomAgent(BaseAgent):
            name = request.name
            version = "1.0.0"
            description = request.description
            icon = request.icon
            
            def _default_system_prompt(self) -> str:
                return request.system_prompt_template
            
            async def execute(self, **kwargs) -> dict:
                return {"status": "success", "message": "Custom agent executed"}
            
            def get_capabilities(self):
                from app.core.agents.base_agent import AgentCapabilities
                caps = []
                for cap_str in request.capabilities:
                    try:
                        caps.append(AgentCapabilities(cap_str))
                    except ValueError:
                        pass
                return caps
        
        agent = CustomAgent(custom_config=request.custom_config)
        agent_id = agent_registry.register(
            agent,
            agent_id=request.name,
            enabled=True,
            metadata={"custom": True, "owner_id": str(current_user.id)}
        )
        
        return {
            "status": "success",
            "agent_id": agent_id,
            "message": f"Agent '{request.name}' registered successfully"
        }
    
    except Exception as e:
        logger.error(f"Failed to register agent: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to register agent: {str(e)}"
        )


@router.put("/{agent_id}")
async def update_agent(
    agent_id: str,
    request: AgentUpdateRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Update agent configuration.
    
    Only works for custom agents registered by the current user.
    """
    agent = agent_registry.get(agent_id)
    
    if not agent:
        raise HTTPException(
            status_code=404,
            detail=f"Agent '{agent_id}' not found"
        )
    
    # Apply updates
    if request.description is not None:
        agent.description = request.description
    
    if request.icon is not None:
        agent.icon = request.icon
    
    if request.system_prompt_template is not None:
        agent.set_system_prompt(request.system_prompt_template)
    
    if request.enabled is not None:
        if request.enabled:
            agent_registry.enable(agent_id)
        else:
            agent_registry.disable(agent_id)
    
    return {
        "status": "success",
        "message": f"Agent '{agent_id}' updated successfully"
    }


@router.delete("/{agent_id}")
async def unregister_agent(
    agent_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Unregister a custom agent.
    
    Cannot unregister built-in agents.
    """
    meta = agent_registry._metadata.get(agent_id, {})
    
    if meta.get("builtin", False):
        raise HTTPException(
            status_code=403,
            detail=f"Cannot unregister built-in agent '{agent_id}'"
        )
    
    success = agent_registry.unregister(agent_id)
    
    if not success:
        raise HTTPException(
            status_code=404,
            detail=f"Agent '{agent_id}' not found"
        )
    
    return {
        "status": "success",
        "message": f"Agent '{agent_id}' unregistered successfully"
    }


@router.get("/capabilities/{capability}")
async def get_agents_by_capability(
    capability: str,
    current_user: User = Depends(get_current_user)
):
    """
    Get all agents that have a specific capability.
    
    Useful for discovering which agents can handle a particular task.
    """
    agents = agent_registry.get_by_capability(capability)
    
    if not agents:
        return {
            "capability": capability,
            "agents": [],
            "total": 0,
            "message": f"No agents found with capability '{capability}'"
        }
    
    return {
        "capability": capability,
        "agents": [a.get_info() for a in agents],
        "total": len(agents)
    }


@router.post("/{agent_id}/execute")
async def execute_agent(
    agent_id: str,
    input_data: dict,
    current_user: User = Depends(get_current_user)
):
    """
    Execute an agent with the provided input.
    
    This is the main endpoint for running agents.
    The input format depends on the specific agent implementation.
    """
    agent = agent_registry.get(agent_id)
    
    if not agent:
        raise HTTPException(
            status_code=404,
            detail=f"Agent '{agent_id}' not found or disabled"
        )
    
    try:
        result = await agent.execute(**input_data)
        return {
            "status": "success",
            "agent_id": agent_id,
            "result": result
        }
    except Exception as e:
        logger.error(f"Agent {agent_id} execution failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Agent execution failed: {str(e)}"
        )


@router.post("/{agent_id}/health")
async def health_check_agent(
    agent_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Check if an agent is healthy and operational.
    """
    agent = agent_registry.get(agent_id)
    
    if not agent:
        raise HTTPException(
            status_code=404,
            detail=f"Agent '{agent_id}' not found or disabled"
        )
    
    healthy = await agent.health_check()
    
    return {
        "agent_id": agent_id,
        "healthy": healthy,
        "name": agent.name,
        "version": agent.version
    }
