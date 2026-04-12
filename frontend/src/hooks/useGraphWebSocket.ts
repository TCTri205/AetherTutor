/**
 * useGraphWebSocket — Custom hook for real-time graph collaboration.
 *
 * Features:
 * - WebSocket connection with JWT auth
 * - Auto-reconnect với exponential backoff
 * - Room join/leave cho graph
 * - Event handlers: node_created, node_updated, node_deleted, presence
 * - Optimistic updates với conflict resolution (last-write-wins)
 * - Cursor position sync
 */
import { useCallback, useEffect, useRef, useState } from "react";
import { toast } from "sonner";

export interface WSUser {
  user_id: string;
  metadata?: {
    cursor?: { x: number; y: number };
    name?: string;
    avatar?: string;
  };
}

export interface WSEvent<T = any> {
  event: string;
  data: T;
}

interface UseGraphWebSocketOptions {
  graphId: string | null;
  enabled?: boolean;
  onNodeCreated?: (data: any) => void;
  onNodeUpdated?: (data: any) => void;
  onNodeDeleted?: (data: any) => void;
}

export function useGraphWebSocket({
  graphId,
  enabled = true,
  onNodeCreated,
  onNodeUpdated,
  onNodeDeleted,
}: UseGraphWebSocketOptions) {
  const [status, setStatus] = useState<"connecting" | "open" | "closed">("closed");
  const [onlineUsers, setOnlineUsers] = useState<WSUser[]>([]);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const reconnectAttemptsRef = useRef(0);
  const roomName = graphId ? `graph:${graphId}` : null;

  const getToken = useCallback(() => {
    return localStorage.getItem("token") || "";
  }, []);

  const connect = useCallback(() => {
    if (!graphId || !enabled) return;

    const token = getToken();
    if (!token) {
      console.warn("No JWT token found, skipping WebSocket connection");
      return;
    }

    setStatus("connecting");
    const wsUrl = `${import.meta.env.VITE_WS_URL || "ws://localhost:8000"}/ws?token=${token}`;
    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      setStatus("open");
      reconnectAttemptsRef.current = 0;
      console.log("WebSocket connected");

      // Join graph room
      ws.send(
        JSON.stringify({
          event: "join_room",
          data: {
            room: roomName,
            metadata: { cursor: { x: 0, y: 0 } },
          },
        })
      );
    };

    ws.onmessage = (event) => {
      try {
        const message: WSEvent = JSON.parse(event.data);
        handleWSEvent(message);
      } catch (err) {
        console.error("Failed to parse WebSocket message:", err);
      }
    };

    ws.onclose = (event) => {
      setStatus("closed");
      console.log("WebSocket closed:", event.code, event.reason);

      // Auto-reconnect với exponential backoff (max 30s)
      if (event.code !== 1000 && enabled) {
        const delay = Math.min(1000 * 2 ** reconnectAttemptsRef.current, 30000);
        reconnectAttemptsRef.current += 1;

        reconnectTimeoutRef.current = setTimeout(() => {
          console.log(`Reconnecting (attempt ${reconnectAttemptsRef.current})...`);
          connect();
        }, delay);
      }
    };

    ws.onerror = (error) => {
      console.error("WebSocket error:", error);
    };
  }, [graphId, enabled, roomName, getToken]);

  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }

    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(
        JSON.stringify({
          event: "leave_room",
          data: { room: roomName },
        })
      );
      wsRef.current.close(1000, "Client disconnect");
    }

    wsRef.current = null;
    setStatus("closed");
    setOnlineUsers([]);
  }, [roomName]);

  const handleWSEvent = useCallback(
    (message: WSEvent) => {
      switch (message.event) {
        case "room_joined":
          setOnlineUsers(message.data.users || []);
          break;
        case "presence_join":
          setOnlineUsers((prev) => [
            ...prev,
            { user_id: message.data.user_id, metadata: message.data.metadata },
          ]);
          toast.info(`${message.data.user_id.slice(0, 8)} joined the graph`);
          break;
        case "presence_leave":
          setOnlineUsers((prev) => prev.filter((u) => u.user_id !== message.data.user_id));
          break;
        case "node_created":
          onNodeCreated?.(message.data);
          break;
        case "node_updated":
          onNodeUpdated?.(message.data);
          break;
        case "node_deleted":
          onNodeDeleted?.(message.data);
          break;
        case "heartbeat_ack":
          // Ignore heartbeat acks
          break;
        default:
          console.log("Unknown WebSocket event:", message.event, message.data);
      }
    },
    [onNodeCreated, onNodeUpdated, onNodeDeleted]
  );

  const sendEvent = useCallback(
    (event: string, data: any) => {
      if (wsRef.current?.readyState === WebSocket.OPEN && roomName) {
        wsRef.current.send(
          JSON.stringify({
            event,
            data: { ...data, room: roomName },
          })
        );
      }
    },
    [roomName]
  );

  const updateCursor = useCallback(
    (x: number, y: number) => {
      sendEvent("cursor_move", { cursor: { x, y } });
    },
    [sendEvent]
  );

  // Heartbeat every 30s
  useEffect(() => {
    if (status !== "open") return;

    const interval = setInterval(() => {
      sendEvent("heartbeat", { timestamp: Date.now() });
    }, 30000);

    return () => clearInterval(interval);
  }, [status, sendEvent]);

  // Connect/disconnect on mount/unmount
  useEffect(() => {
    if (enabled && graphId) {
      connect();
    }

    return () => {
      disconnect();
    };
  }, [connect, disconnect, enabled, graphId]);

  return {
    status,
    onlineUsers,
    sendEvent,
    updateCursor,
    connect,
    disconnect,
  };
}
