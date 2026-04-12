"""
WebSocket endpoint handlers for real-time collaboration.

Endpoints:
- GET /ws?token=<jwt> — Main WebSocket endpoint
- GET /ws/graph/{graph_id}?token=<jwt> — Graph collaboration room
- GET /ws/team/{team_id}?token=<jwt> — Team presence room
"""
from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from loguru import logger

from app.api.websocket import ws_manager, get_websocket_user

router = APIRouter(tags=["websocket"])


@router.get("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    token: str = Query(..., description="JWT access token"),
):
    """
    Main WebSocket endpoint for real-time collaboration.
    
    After connecting, client can join rooms:
    - graph:{graph_id} — Graph events
    - team:{team_id} — Team events
    - chat:{conv_id} — Chat events
    
    Message format:
    {
        "event": "<event_type>",
        "data": { ... }
    }
    
    Events sent by server:
    - presence_join — User joined a room
    - presence_leave — User left a room
    - node_created — New node created
    - node_updated — Node updated
    - node_deleted — Node deleted
    - resource_shared — Resource shared with team
    - conflict — Concurrent edit conflict detected
    
    Events from client:
    - join_room — Join a room
    - leave_room — Leave a room
    - heartbeat — Keep-alive ping
    - node_create — Create a node
    - node_update — Update a node
    - node_delete — Delete a node
    """
    # Authenticate
    try:
        payload = await get_websocket_user(token)
        user_id = payload["sub"]
    except Exception as e:
        await websocket.close(code=4001, reason=str(e))
        return

    connection_id = str(uuid.uuid4())
    await ws_manager.connect(websocket, connection_id, user_id)

    try:
        while True:
            # Wait for messages
            data = await websocket.receive_json()
            await handle_message(connection_id, user_id, data)
    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.error(f"WebSocket error for {connection_id}: {e}")
    finally:
        user_id = ws_manager.disconnect(connection_id)
        if user_id:
            # Notify rooms about disconnect
            for room_name in list(ws_manager.rooms.keys()):
                members = ws_manager.get_room_members(room_name)
                if any(m["connection_id"] == connection_id for m in members):
                    await ws_manager.broadcast_to_room(room_name, {
                        "event": "presence_leave",
                        "data": {
                            "user_id": user_id,
                            "connection_id": connection_id,
                            "reason": "disconnected",
                        },
                    })


async def handle_message(connection_id: str, user_id: str, data: dict[str, Any]):
    """Route incoming WebSocket messages."""
    event = data.get("event")
    payload = data.get("data", {})

    if event == "join_room":
        await handle_join_room(connection_id, user_id, payload)
    elif event == "leave_room":
        await handle_leave_room(connection_id, user_id, payload)
    elif event == "heartbeat":
        await ws_manager.send_heartbeat(connection_id)
        await ws_manager.send_to_connection(connection_id, {
            "event": "heartbeat_ack",
            "data": {"timestamp": payload.get("timestamp")},
        })
    elif event == "node_create":
        await handle_node_event(connection_id, user_id, "node_created", payload)
    elif event == "node_update":
        await handle_node_event(connection_id, user_id, "node_updated", payload)
    elif event == "node_delete":
        await handle_node_event(connection_id, user_id, "node_deleted", payload)
    else:
        logger.warning(f"Unknown WebSocket event: {event}")


async def handle_join_room(connection_id: str, user_id: str, payload: dict):
    """Join a room (graph:{id}, team:{id}, chat:{id})."""
    room_name = payload.get("room")
    if not room_name:
        return

    ws_manager.add_to_room(connection_id, room_name)

    # Get connection metadata (cursor position, etc)
    metadata = payload.get("metadata", {})

    # Notify others in room
    await ws_manager.broadcast_to_room(
        room_name,
        {
            "event": "presence_join",
            "data": {
                "user_id": user_id,
                "connection_id": connection_id,
                "metadata": metadata,
            },
        },
        exclude_connection_id=connection_id,
    )

    # Send room state back to user
    online_users = ws_manager.get_online_users_in_room(room_name)
    await ws_manager.send_to_connection(connection_id, {
        "event": "room_joined",
        "data": {
            "room": room_name,
            "users": online_users,
        },
    })

    logger.debug(f"User {user_id} joined room {room_name}")


async def handle_leave_room(connection_id: str, user_id: str, payload: dict):
    """Leave a room."""
    room_name = payload.get("room")
    if not room_name:
        return

    ws_manager.remove_from_room(connection_id, room_name)

    # Notify others
    await ws_manager.broadcast_to_room(room_name, {
        "event": "presence_leave",
        "data": {
            "user_id": user_id,
            "connection_id": connection_id,
        },
    }, exclude_connection_id=connection_id)

    logger.debug(f"User {user_id} left room {room_name}")


async def handle_node_event(
    connection_id: str, user_id: str, event_type: str, payload: dict
):
    """Broadcast node events to room with last-write-wins conflict resolution."""
    room = payload.get("room")
    if not room:
        return

    # Add vector clock for conflict resolution
    import time
    payload["vector_clock"] = {
        "user_id": user_id,
        "timestamp": time.time(),
        "connection_id": connection_id,
    }

    # Broadcast to room
    sent = await ws_manager.broadcast_to_room(
        room,
        {
            "event": event_type,
            "data": payload,
        },
        exclude_connection_id=connection_id,
    )

    logger.debug(
        f"Broadcast {event_type} to {sent} connections in room {room}"
    )
