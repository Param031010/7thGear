from datetime import datetime, timezone
from typing import Any, Optional

from api.websocket import manager
from models.schemas import EventType
from repositories.event_repository import EventRepository


class EventEmitter:
    """Every significant thing the agent does goes through here exactly
    once: persisted to execution_events (the audit trail / source of truth)
    and broadcast to any Electron windows watching this run over WebSocket.
    """

    def __init__(self, run_id: str, repository: Optional[EventRepository] = None):
        self.run_id = run_id
        self._repo = repository or EventRepository()

    async def emit(
        self,
        event_type: EventType,
        tool_name: Optional[str] = None,
        input: Optional[dict[str, Any]] = None,
        output: Optional[dict[str, Any]] = None,
        status: Optional[str] = None,
        error: Optional[str] = None,
    ) -> None:
        self._repo.append(
            run_id=self.run_id,
            event_type=event_type.value,
            tool_name=tool_name,
            input=input,
            output=output,
            status=status,
            error=error,
        )
        await manager.broadcast(
            self.run_id,
            {
                "event_type": event_type.value,
                "tool_name": tool_name,
                "input": input,
                "output": output,
                "status": status,
                "error": error,
                "created_at": datetime.now(timezone.utc).isoformat(),
            },
        )
