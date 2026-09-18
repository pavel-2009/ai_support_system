"""Менеджер WebSocket-соединений операторов."""

from collections import defaultdict
from typing import Any

from fastapi import WebSocket


class OperatorConnectionManager:
    """Управляет WebSocket-соединениями операторов."""

    def __init__(self) -> None:
        self._connections: dict[int, set[WebSocket]] = defaultdict(set)

    async def connect(self, operator_id: int, websocket: WebSocket) -> None:
        """Принять WebSocket и зарегистрировать оператора."""
        await websocket.accept()
        self._connections[operator_id].add(websocket)

    def disconnect(self, operator_id: int, websocket: WebSocket) -> None:
        """Удалить WebSocket-соединение оператора."""
        connections = self._connections.get(operator_id)

        if not connections:
            return

        connections.discard(websocket)

        if not connections:
            self._connections.pop(operator_id, None)

    async def broadcast(self, message: dict[str, Any]) -> None:
        """Отправить сообщение всем подключённым операторам."""
        disconnected: list[tuple[int, WebSocket]] = []

        for operator_id, connections in self._connections.items():
            for websocket in connections.copy():
                try:
                    await websocket.send_json(message)
                except Exception:
                    disconnected.append((operator_id, websocket))

        for operator_id, websocket in disconnected:
            self.disconnect(operator_id, websocket)


operator_connection_manager = OperatorConnectionManager()