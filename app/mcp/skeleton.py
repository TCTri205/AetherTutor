from pydantic import BaseModel
from typing import Optional, Dict, Any

class MCPContext(BaseModel):
    user_id: str
    session_id: str
    metadata: Dict[str, Any] = {}

class MCPSkeleton:
    """
    Model Context Protocol (MCP) Skeleton
    This will provide a standardized way for agents to share and 
    access context within the Learning OS.
    """
    def __init__(self):
        self._contexts = {}

    def update_context(self, context: MCPContext):
        self._contexts[context.session_id] = context
        return True

    def get_context(self, session_id: str) -> Optional[MCPContext]:
        return self._contexts.get(session_id)


mcp_skeleton = MCPSkeleton()
