import asyncio
from typing import Dict, List

from fastapi import WebSocket


class RestaurantOrderConnectionManager:
    """Tracks WebSocket clients subscribed to a restaurant's live order feed
    and broadcasts order events (created / status changed / items changed) to them."""

    def __init__(self) -> None:
        self._connections: Dict[int, List[WebSocket]] = {}
        self._lock = asyncio.Lock()

    async def connect(self, restaurant_id: int, websocket: WebSocket) -> None:
        await websocket.accept()
        async with self._lock:
            self._connections.setdefault(restaurant_id, []).append(websocket)

    async def disconnect(self, restaurant_id: int, websocket: WebSocket) -> None:
        async with self._lock:
            connections = self._connections.get(restaurant_id)
            if not connections:
                return
            if websocket in connections:
                connections.remove(websocket)
            if not connections:
                self._connections.pop(restaurant_id, None)

    async def broadcast(self, restaurant_id: int, message: dict) -> None:
        async with self._lock:
            connections = list(self._connections.get(restaurant_id, []))

        dead: List[WebSocket] = []
        for connection in connections:
            try:
                await connection.send_json(message)
            except Exception:
                dead.append(connection)

        if dead:
            async with self._lock:
                connections = self._connections.get(restaurant_id)
                if connections:
                    for connection in dead:
                        if connection in connections:
                            connections.remove(connection)
                    if not connections:
                        self._connections.pop(restaurant_id, None)


restaurant_ws_manager = RestaurantOrderConnectionManager()
