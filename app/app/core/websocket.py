"""WebSocket manager for conversation escalation handling."""

from typing import Dict, Set
from fastapi import WebSocket


class WebSocketManager:
    """Manages WebSocket connections for conversation escalation."""

    def __init__(self):
        """Initialize the WebSocketManager with an empty connection dictionary."""
        self.active_connections: Dict[int, Set] = {}

    def connect(self, conversation_id: int, websocket: WebSocket):
        """Add a new WebSocket connection for a specific conversation."""
        if conversation_id not in self.active_connections:
            self.active_connections[conversation_id] = set()
        self.active_connections[conversation_id].add(websocket)

    def disconnect(self, conversation_id: int, websocket: WebSocket):
        """Remove a WebSocket connection for a specific conversation."""
        if conversation_id in self.active_connections:
            self.active_connections[conversation_id].discard(websocket)
            if not self.active_connections[conversation_id]:
                del self.active_connections[conversation_id]

    def send_to_operator(self, conversation_id: int, message: str):
        """Send a message to all WebSocket connections associated with a specific conversation."""
        if conversation_id in self.active_connections:
            for websocket in self.active_connections[conversation_id]:
                websocket.send_text(message)

    def broadcast(self, message: str):
        """Send a message to all active WebSocket connections across all conversations."""
        for connections in self.active_connections.values():
            for websocket in connections:
                websocket.send_text(message)
