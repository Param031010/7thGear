"""In-memory stand-ins for the Supabase-backed repositories, used so the
agent/executor/orchestrator logic can be unit tested without a real Supabase
project. Each fake duck-types the real repository's public methods.
"""

import uuid
from typing import Any, Optional


class FakeStateRepository:
    def __init__(self) -> None:
        self._rows: dict[str, dict[str, Any]] = {}

    def upsert(self, run_id: str, state: dict, facts: dict, execution_history: list) -> None:
        self._rows[run_id] = {"run_id": run_id, "state": state, "facts": facts, "execution_history": execution_history}

    def get(self, run_id: str) -> Optional[dict[str, Any]]:
        row = self._rows.get(run_id)
        return dict(row) if row else None


class FakeEventRepository:
    def __init__(self) -> None:
        self.rows: list[dict[str, Any]] = []

    def append(self, run_id, event_type, tool_name=None, input=None, output=None, status=None, error=None):
        row = {
            "id": str(uuid.uuid4()),
            "run_id": run_id,
            "event_type": event_type,
            "tool_name": tool_name,
            "input": input or {},
            "output": output or {},
            "status": status,
            "error": error,
        }
        self.rows.append(row)
        return row

    def list_for_run(self, run_id: str) -> list[dict[str, Any]]:
        return [r for r in self.rows if r["run_id"] == run_id]


class FakeRunRepository:
    def __init__(self) -> None:
        self._rows: dict[str, dict[str, Any]] = {}

    def create(self, workflow_id, goal) -> dict[str, Any]:
        run_id = str(uuid.uuid4())
        row = {
            "id": run_id,
            "workflow_id": workflow_id,
            "goal": goal,
            "status": "pending",
            "current_step": None,
            "started_at": None,
            "completed_at": None,
            "created_at": "2026-01-01T00:00:00+00:00",
        }
        self._rows[run_id] = row
        return row

    def get(self, run_id: str) -> Optional[dict[str, Any]]:
        return self._rows.get(run_id)

    def list(self) -> list[dict[str, Any]]:
        return list(self._rows.values())

    def update_status(self, run_id, status, current_step=None, started=False, completed=False) -> None:
        row = self._rows[run_id]
        row["status"] = status
        if current_step is not None:
            row["current_step"] = current_step
        if started:
            row["started_at"] = "2026-01-01T00:00:00+00:00"
        if completed:
            row["completed_at"] = "2026-01-01T00:05:00+00:00"


class FakeApprovalRepository:
    def __init__(self) -> None:
        self._rows: dict[str, dict[str, Any]] = {}

    def create(self, run_id, approval_type) -> dict[str, Any]:
        approval_id = str(uuid.uuid4())
        row = {"id": approval_id, "run_id": run_id, "approval_type": approval_type, "status": "pending", "response": None}
        self._rows[approval_id] = row
        return row

    def get(self, approval_id: str) -> Optional[dict[str, Any]]:
        return self._rows.get(approval_id)

    def latest_pending_for_run(self, run_id, approval_type=None):
        candidates = [r for r in self._rows.values() if r["run_id"] == run_id and r["status"] == "pending"]
        if approval_type:
            candidates = [r for r in candidates if r["approval_type"] == approval_type]
        return candidates[-1] if candidates else None

    def resolve(self, approval_id, status, response=None) -> None:
        row = self._rows[approval_id]
        row["status"] = status
        row["response"] = response or {}
