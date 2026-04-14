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

import uuid
from fastapi import APIRouter, HTTPException, Depends
import logging

from app.schemas.agent import (
    AgentInfo, AgentListResponse,
    AgentCreateRequest, AgentUpdateRequest
)
from app.core.agents.registry import agent_registry
from app.api.dependencies import get_current_user_id

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/agents", tags=["agents"])


@router.get("", response_model=AgentListResponse)
async def list_agents(
    enabled_only: bool = True,
    user_id: uuid.UUID = Depends(get_current_user_id)
):
    """
    List all available agents.
    
    Returns agent information including name, description, capabilities,
    and configuration schema for UI rendering.
    """
    agents = agent_registry.list_agents(enabled_only=enabled_only)

    # Add enabled status (agents in list are enabled by definition)
    for agent_info in agents:
        agent_info["enabled"] = True

    return AgentListResponse(
        agents=[AgentInfo(**a) for a in agents],
        total=len(agents)
    )


@router.get("/{agent_id}", response_model=AgentInfo)
async def get_agent(
    agent_id: str,
    user_id: uuid.UUID = Depends(get_current_user_id)
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
    info["enabled"] = True  # If agent is in registry and returned, it's enabled
    return AgentInfo(**info)


@router.post("", status_code=201)
async def register_agent(
    request: AgentCreateRequest,
    user_id: uuid.UUID = Depends(get_current_user_id)
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
    
    # Create a custom agent instance using factory pattern
    from app.core.agents.custom_agent import CustomAgent
    from app.core.agents.base_agent import AgentCapabilities

    caps = []
    for cap_str in request.capabilities:
        try:
            caps.append(AgentCapabilities(cap_str))
        except ValueError:
            pass

    agent = CustomAgent(
        name=request.name,
        description=request.description,
        system_prompt=request.system_prompt_template,
        capabilities=caps,
        icon=request.icon,
        custom_config=request.custom_config,
    )

    try:
        agent_id = agent_registry.register(
            agent,
            agent_id=request.name,
            enabled=True,
            metadata={"custom": True, "owner_id": str(user_id)}
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
            detail="Failed to register agent"
        )


@router.put("/{agent_id}")
async def update_agent(
    agent_id: str,
    request: AgentUpdateRequest,
    user_id: uuid.UUID = Depends(get_current_user_id)
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

    # Verify ownership for custom agents
    meta = agent_registry._metadata.get(agent_id, {})
    agent_meta = meta.get("metadata", {})
    if agent_meta.get("custom"):
        owner_id = agent_meta.get("owner_id")
        if owner_id and str(user_id) != owner_id:
            raise HTTPException(
                status_code=403,
                detail="Not the agent owner"
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
    user_id: uuid.UUID = Depends(get_current_user_id)
):
    """
    Unregister a custom agent.

    Cannot unregister built-in agents.
    """
    meta = agent_registry._metadata.get(agent_id, {})
    agent_meta = meta.get("metadata", {})

    if agent_meta.get("builtin", False):
        raise HTTPException(
            status_code=403,
            detail=f"Cannot unregister built-in agent '{agent_id}'"
        )

    # Verify ownership for custom agents
    if agent_meta.get("custom"):
        owner_id = agent_meta.get("owner_id")
        if owner_id and str(user_id) != owner_id:
            raise HTTPException(
                status_code=403,
                detail="Not the agent owner"
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
    user_id: uuid.UUID = Depends(get_current_user_id)
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
    user_id: uuid.UUID = Depends(get_current_user_id)
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
            detail="Agent execution failed"
        )


@router.post("/{agent_id}/health")
async def health_check_agent(
    agent_id: str,
    user_id: uuid.UUID = Depends(get_current_user_id)
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
