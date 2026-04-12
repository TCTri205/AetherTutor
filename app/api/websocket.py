"""
WebSocket Manager for real-time collaboration.

Manages WebSocket connections, rooms, and message broadcasting.
Supports JWT authentication via query parameter.
"""
from __future__ import annotations

import asyncio
import json
import uuid
from datetime import datetime
from typing import Any, Optional

from fastapi import WebSocket, WebSocketDisconnect, Query, Depends, HTTPException
from loguru import logger

from app.services.security import decode_token


class ConnectionManager:
    """
    Manages WebSocket connections with room-based broadcasting.
    
    Rooms:
    - graph:{graph_id} — Real-time graph collaboration
    - chat:{conv_id} — Real-time chat collaboration
    - team:{team_id} — Team presence and events
    """

    def __init__(self) -> None:
        # connection_id -> {websocket, user_id, rooms, metadata}
        self.active_connections: dict[str, dict[str, Any]] = {}
        # room_name -> set of connection_ids
        self.rooms: dict[str, set[str]] = {}
        # user_id -> set of connection_ids (track multiple devices)
        self.user_connections: dict[str, set[str]] = {}

    async def connect(
        self,
        websocket: WebSocket,
        connection_id: str,
        user_id: str,
        metadata: dict | None = None,
    ) -> None:
        """Accept a new WebSocket connection."""
        await websocket.accept()
        self.active_connections[connection_id] = {
            "websocket": websocket,
            "user_id": user_id,
            "rooms": set(),
            "metadata": metadata or {},
            "connected_at": datetime.utcnow().isoformat(),
            "last_heartbeat": datetime.utcnow().isoformat(),
        }
        if user_id not in self.user_connections:
            self.user_connections[user_id] = set()
        self.user_connections[user_id].add(connection_id)
        logger.info(
            f"WebSocket connected: {connection_id} (user={user_id})"
        )

    def disconnect(self, connection_id: str) -> Optional[str]:
        """
        Disconnect a WebSocket connection and remove from all rooms.
        Returns user_id if connection existed.
        """
        conn = self.active_connections.pop(connection_id, None)
        if not conn:
            return None

        user_id = conn["user_id"]
        # Remove from all rooms
        for room_name in list(conn["rooms"]):
            self.remove_from_room(connection_id, room_name)

        # Remove from user connections
        if user_id in self.user_connections:
            self.user_connections[user_id].discard(connection_id)
            if not self.user_connections[user_id]:
                del self.user_connections[user_id]

        logger.info(
            f"WebSocket disconnected: {connection_id} (user={user_id})"
        )
        return user_id

    def add_to_room(self, connection_id: str, room_name: str) -> bool:
        """Add a connection to a room."""
        if connection_id not in self.active_connections:
            return False

        if room_name not in self.rooms:
            self.rooms[room_name] = set()

        self.rooms[room_name].add(connection_id)
        self.active_connections[connection_id]["rooms"].add(room_name)
        logger.debug(f"Connection {connection_id} joined room {room_name}")
        return True

    def remove_from_room(self, connection_id: str, room_name: str) -> None:
        """Remove a connection from a room."""
        if room_name in self.rooms:
            self.rooms[room_name].discard(connection_id)
            if not self.rooms[room_name]:
                del self.rooms[room_name]

        if connection_id in self.active_connections:
            self.active_connections[connection_id]["rooms"].discard(room_name)

    async def send_to_connection(
        self, connection_id: str, message: dict[str, Any]
    ) -> bool:
        """Send a message to a specific connection."""
        conn = self.active_connections.get(connection_id)
        if not conn:
            return False

        try:
            await conn["websocket"].send_json(message)
            return True
        except Exception as e:
            logger.error(f"Failed to send to {connection_id}: {e}")
            return False

    async def broadcast_to_room(
        self,
        room_name: str,
        message: dict[str, Any],
        exclude_connection_id: Optional[str] = None,
    ) -> int:
        """Broadcast a message to all connections in a room."""
        room = self.rooms.get(room_name, set())
        if not room:
            return 0

        sent_count = 0
        for conn_id in list(room):
            if conn_id == exclude_connection_id:
                continue
            if await self.send_to_connection(conn_id, message):
                sent_count += 1

        return sent_count

    async def broadcast_to_user(
        self, user_id: str, message: dict[str, Any]
    ) -> int:
        """Send a message to all connections of a user (multi-device)."""
        conn_ids = self.user_connections.get(user_id, set())
        if not conn_ids:
            return 0

        sent_count = 0
        for conn_id in conn_ids:
            if await self.send_to_connection(conn_id, message):
                sent_count += 1
        return sent_count

    def get_room_members(self, room_name: str) -> list[dict[str, Any]]:
        """Get all connections in a room with user info."""
        room = self.rooms.get(room_name, set())
        members = []
        for conn_id in room:
            conn = self.active_connections.get(conn_id)
            if conn:
                members.append({
                    "connection_id": conn_id,
                    "user_id": conn["user_id"],
                    "metadata": conn["metadata"],
                })
        return members

    def get_user_rooms(self, user_id: str) -> list[str]:
        """Get all rooms a user is currently in."""
        rooms = []
        for conn_id in self.user_connections.get(user_id, set()):
            conn = self.active_connections.get(conn_id)
            if conn:
                rooms.extend(conn["rooms"])
        return list(set(rooms))

    def get_room_count(self, room_name: str) -> int:
        """Get number of connections in a room."""
        return len(self.rooms.get(room_name, set()))

    def get_online_users_in_room(self, room_name: str) -> list[dict[str, str]]:
        """Get unique users in a room (deduplicated by user_id)."""
        members = self.get_room_members(room_name)
        seen = set()
        users = []
        for m in members:
            if m["user_id"] not in seen:
                seen.add(m["user_id"])
                users.append({
                    "user_id": m["user_id"],
                    "metadata": m["metadata"],
                })
        return users

    def get_connection_stats(self) -> dict[str, Any]:
        """Get overall connection statistics."""
        return {
            "total_connections": len(self.active_connections),
            "total_rooms": len(self.rooms),
            "unique_users": len(self.user_connections),
        }

    async def send_heartbeat(self, connection_id: str) -> bool:
        """Update heartbeat timestamp for a connection."""
        conn = self.active_connections.get(connection_id)
        if conn:
            conn["last_heartbeat"] = datetime.utcnow().isoformat()
            return True
        return False


# Global singleton
ws_manager = ConnectionManager()


# === WebSocket Authentication ===

async def get_websocket_user(
    token: str = Query(..., description="JWT access token"),
) -> dict:
    """
    Authenticate WebSocket connection via JWT token in query param.
    
    Usage: ws://host/ws?token=<jwt_token>
    """
    try:
        payload = decode_token(token)
        if payload.get("type") != "access":
            raise HTTPException(status_code=401, detail="Invalid token type")
        return payload
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Authentication failed: {e}")


async def cleanup_stale_connections(manager: ConnectionManager) -> int:
    """
    Remove connections that haven't sent heartbeat in >60s.
    Call this periodically (every 30s).
    """
    import time
    now = time.time()
    stale_ids = []
    
    for conn_id, conn in list(manager.active_connections.items()):
        last_hb = datetime.fromisoformat(conn["last_heartbeat"])
        if (now - last_hb.timestamp()) > 60:
            stale_ids.append(conn_id)
    
    for conn_id in stale_ids:
        manager.disconnect(conn_id)
    
    return len(stale_ids)
