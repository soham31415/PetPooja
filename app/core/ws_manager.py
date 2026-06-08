import asyncio
from typing import Dict, Hashable, List

from fastapi import WebSocket


class ConnectionManager:
    """Tracks WebSocket clients subscribed by some key (restaurant id, session
    id, ...) and broadcasts JSON payloads to all of them."""

    def __init__(self) -> None:
        self._connections: Dict[Hashable, List[WebSocket]] = {}
        self._lock = asyncio.Lock()

    async def connect(self, key: Hashable, websocket: WebSocket) -> None:
        await websocket.accept()
        async with self._lock:
            self._connections.setdefault(key, []).append(websocket)

    async def disconnect(self, key: Hashable, websocket: WebSocket) -> None:
        async with self._lock:
            connections = self._connections.get(key)
            if not connections:
                return
            if websocket in connections:
                connections.remove(websocket)
            if not connections:
                self._connections.pop(key, None)

    async def broadcast(self, key: Hashable, message: dict) -> None:
        async with self._lock:
            connections = list(self._connections.get(key, []))

        dead: List[WebSocket] = []
        for connection in connections:
            try:
                await connection.send_json(message)
            except Exception:
                dead.append(connection)

        if dead:
            async with self._lock:
                connections = self._connections.get(key)
                if connections:
                    for connection in dead:
                        if connection in connections:
                            connections.remove(connection)
                    if not connections:
                        self._connections.pop(key, None)


# Restaurant owners watching their live order dashboard
restaurant_ws_manager = ConnectionManager()

# Session participants watching their own session's order updates
session_ws_manager = ConnectionManager()
