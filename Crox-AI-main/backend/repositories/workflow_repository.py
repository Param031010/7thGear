from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from database.client import get_supabase


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class WorkflowRepository:
    """Persists workflow definitions and their high-level steps."""

    table = "workflows"
    steps_table = "workflow_steps"

    def create(self, name: str, goal: str, plan: dict[str, Any], description: str = "") -> dict[str, Any]:
        client = get_supabase()
        row = {
            "name": name,
            "description": description,
            "goal": goal,
            "plan": plan,
            "status": "draft",
        }
        result = client.table(self.table).insert(row).execute()
        workflow = result.data[0]

        steps = plan.get("steps", [])
        if steps:
            step_rows = [
                {
                    "workflow_id": workflow["id"],
                    "step_order": idx,
                    "objective": step["objective"],
                    "metadata": {"id": step["id"]},
                }
                for idx, step in enumerate(steps)
            ]
            client.table(self.steps_table).insert(step_rows).execute()

        return workflow

    def get(self, workflow_id: str) -> Optional[dict[str, Any]]:
        client = get_supabase()
        result = client.table(self.table).select("*").eq("id", workflow_id).limit(1).execute()
        return result.data[0] if result.data else None

    def list(self) -> list[dict[str, Any]]:
        client = get_supabase()
        result = client.table(self.table).select("*").order("created_at", desc=True).execute()
        return result.data

    def delete(self, workflow_id: str) -> None:
        client = get_supabase()
        client.table(self.table).delete().eq("id", workflow_id).execute()

    def set_status(self, workflow_id: str, status: str) -> None:
        client = get_supabase()
        client.table(self.table).update({"status": status, "updated_at": _now()}).eq("id", workflow_id).execute()

    def get_steps(self, workflow_id: str) -> list[dict[str, Any]]:
        client = get_supabase()
        result = (
            client.table(self.steps_table)
            .select("*")
            .eq("workflow_id", workflow_id)
            .order("step_order")
            .execute()
        )
        return result.data
