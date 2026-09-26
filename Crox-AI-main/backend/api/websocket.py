import json
from typing import Any

from fastapi import WebSocket


class ConnectionManager:
    """Tracks live WebSocket connections per run_id and broadcasts events to
    all of them. A single Electron window can have multiple listeners open
    (e.g. execution details + dashboard), so this fans out to all of them.
    """

    def __init__(self) -> None:
        self._connections: dict[str, list[WebSocket]] = {}

    async def connect(self, run_id: str, websocket: WebSocket) -> None:
        await websocket.accept()
        self._connections.setdefault(run_id, []).append(websocket)

    def disconnect(self, run_id: str, websocket: WebSocket) -> None:
        if run_id in self._connections and websocket in self._connections[run_id]:
            self._connections[run_id].remove(websocket)
            if not self._connections[run_id]:
                del self._connections[run_id]

    async def broadcast(self, run_id: str, payload: dict[str, Any]) -> None:
        for websocket in list(self._connections.get(run_id, [])):
            try:
                await websocket.send_text(json.dumps(payload, default=str))
            except Exception:  # noqa: BLE001 - a dead socket shouldn't break the run
                self.disconnect(run_id, websocket)


manager = ConnectionManager()
