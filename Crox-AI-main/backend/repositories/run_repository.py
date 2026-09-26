from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from database.client import get_supabase


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class RunRepository:
    table = "workflow_runs"

    def create(self, workflow_id: Optional[str], goal: str) -> dict[str, Any]:
        client = get_supabase()
        row = {
            "workflow_id": workflow_id,
            "goal": goal,
            "status": "pending",
        }
        result = client.table(self.table).insert(row).execute()
        return result.data[0]

    def get(self, run_id: str) -> Optional[dict[str, Any]]:
        client = get_supabase()
        result = client.table(self.table).select("*").eq("id", run_id).limit(1).execute()
        return result.data[0] if result.data else None

    def list(self) -> list[dict[str, Any]]:
        client = get_supabase()
        result = client.table(self.table).select("*").order("created_at", desc=True).execute()
        return result.data

    def delete(self, run_id: str) -> None:
        client = get_supabase()
        client.table(self.table).delete().eq("id", run_id).execute()

    def update_status(
        self,
        run_id: str,
        status: str,
        current_step: Optional[str] = None,
        started: bool = False,
        completed: bool = False,
    ) -> None:
        client = get_supabase()
        patch: dict[str, Any] = {"status": status}
        if current_step is not None:
            patch["current_step"] = current_step
        if started:
            patch["started_at"] = _now()
        if completed:
            patch["completed_at"] = _now()
        client.table(self.table).update(patch).eq("id", run_id).execute()
