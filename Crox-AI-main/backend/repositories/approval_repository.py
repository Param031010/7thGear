from datetime import datetime, timezone
from typing import Any, Optional

from database.client import get_supabase


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class ApprovalRepository:
    table = "approvals"

    def create(self, run_id: str, approval_type: str) -> dict[str, Any]:
        client = get_supabase()
        row = {"run_id": run_id, "approval_type": approval_type, "status": "pending"}
        result = client.table(self.table).insert(row).execute()
        return result.data[0]

    def get(self, approval_id: str) -> Optional[dict[str, Any]]:
        client = get_supabase()
        result = client.table(self.table).select("*").eq("id", approval_id).limit(1).execute()
        return result.data[0] if result.data else None

    def latest_pending_for_run(self, run_id: str, approval_type: Optional[str] = None) -> Optional[dict[str, Any]]:
        client = get_supabase()
        query = client.table(self.table).select("*").eq("run_id", run_id).eq("status", "pending")
        if approval_type:
            query = query.eq("approval_type", approval_type)
        result = query.order("created_at", desc=True).limit(1).execute()
        return result.data[0] if result.data else None

    def resolve(self, approval_id: str, status: str, response: Optional[dict[str, Any]] = None) -> None:
        client = get_supabase()
        client.table(self.table).update(
            {"status": status, "response": response or {}, "updated_at": _now()}
        ).eq("id", approval_id).execute()
