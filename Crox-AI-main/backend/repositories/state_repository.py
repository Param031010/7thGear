from datetime import datetime, timezone
from typing import Any, Optional

from database.client import get_supabase


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class StateRepository:
    """Persists agent_state so a run can be recovered after a backend restart."""

    table = "agent_state"

    def upsert(self, run_id: str, state: dict[str, Any], facts: dict[str, Any], execution_history: list[Any]) -> None:
        client = get_supabase()
        row = {
            "run_id": run_id,
            "state": state,
            "facts": facts,
            "execution_history": execution_history,
            "updated_at": _now(),
        }
        client.table(self.table).upsert(row, on_conflict="run_id").execute()

    def get(self, run_id: str) -> Optional[dict[str, Any]]:
        client = get_supabase()
        result = client.table(self.table).select("*").eq("run_id", run_id).limit(1).execute()
        return result.data[0] if result.data else None
