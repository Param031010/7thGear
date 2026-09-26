from typing import Any, Optional

from database.client import get_supabase


class EventRepository:
    """Append-only audit trail for a workflow run."""

    table = "execution_events"

    def append(
        self,
        run_id: str,
        event_type: str,
        tool_name: Optional[str] = None,
        input: Optional[dict[str, Any]] = None,
        output: Optional[dict[str, Any]] = None,
        status: Optional[str] = None,
        error: Optional[str] = None,
    ) -> dict[str, Any]:
        client = get_supabase()
        row = {
            "run_id": run_id,
            "event_type": event_type,
            "tool_name": tool_name,
            "input": input or {},
            "output": output or {},
            "status": status,
            "error": error,
        }
        result = client.table(self.table).insert(row).execute()
        return result.data[0]

    def list_for_run(self, run_id: str) -> list[dict[str, Any]]:
        client = get_supabase()
        result = (
            client.table(self.table)
            .select("*")
            .eq("run_id", run_id)
            .order("created_at")
            .execute()
        )
        return result.data
