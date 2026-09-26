import json
from pathlib import Path
from typing import Any, Optional

from pydantic import BaseModel, field_validator

from models.schemas import ToolResult
from tools.base import Tool

FIXTURES_DIR = Path(__file__).resolve().parent.parent.parent / "fixtures"

# Module-level in-memory tracker, seeded once per backend process. This is the
# "mock" replacement for a real Google Sheet during DEMO_MODE -- swap this
# module out for tools/sheets.py (Google Sheets API) to go live.
_tracker: dict[str, dict[str, Any]] = {}
_next_id = 1025


def _seed() -> None:
    global _next_id
    if _tracker:
        return
    with open(FIXTURES_DIR / "tracker_seed.json", encoding="utf-8") as f:
        seed = json.load(f)["records"]
    for record in seed:
        _tracker[record["record_id"]] = record


def reset_tracker() -> None:
    """Used by tests to get a clean tracker between scenarios."""
    global _next_id
    _tracker.clear()
    _next_id = 1025
    _seed()


class SheetsSearchArgs(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None


class MockSheetsSearchTool(Tool):
    name = "sheets.search"
    description = "Search the candidate tracker by name or email. Returns whether a matching record exists."
    input_model = SheetsSearchArgs

    async def run(self, arguments: SheetsSearchArgs) -> ToolResult:
        _seed()
        for record in _tracker.values():
            if arguments.email and record.get("email") == arguments.email:
                return ToolResult(success=True, data={"found": True, "record_id": record["record_id"], "record": record})
            if arguments.name and record.get("name", "").lower() == arguments.name.lower():
                return ToolResult(success=True, data={"found": True, "record_id": record["record_id"], "record": record})
        return ToolResult(success=True, data={"found": False})


class SheetsInsertArgs(BaseModel):
    name: str
    email: str
    phone: str = ""
    college: str = ""
    skills: list[str] = []

    @field_validator("skills", mode="before")
    @classmethod
    def _normalize_skills(cls, v: Any) -> list[str]:
        if isinstance(v, list):
            return [str(s).strip() for s in v if str(s).strip()]
        if isinstance(v, str):
            return [s.strip() for s in v.split(",") if s.strip()]
        return []


class MockSheetsInsertTool(Tool):
    name = "sheets.insert"
    description = (
        "Insert a new candidate record into the tracker. Only call this when sheets.search found no match. "
        "'skills' must be a JSON array of strings, e.g. [\"Python\", \"SQL\"] -- not a comma-separated string."
    )
    input_model = SheetsInsertArgs

    async def run(self, arguments: SheetsInsertArgs) -> ToolResult:
        global _next_id
        _seed()
        for record in _tracker.values():
            if record.get("email") == arguments.email:
                return ToolResult(
                    success=False,
                    error=f"candidate with email {arguments.email} already exists as {record['record_id']}",
                )
        record_id = f"C{_next_id}"
        _next_id += 1
        record = {
            "record_id": record_id,
            "name": arguments.name,
            "email": arguments.email,
            "phone": arguments.phone,
            "college": arguments.college,
            "skills": arguments.skills,
            "status": "applied",
        }
        _tracker[record_id] = record
        return ToolResult(success=True, data={"record_id": record_id, "record": record})


class SheetsUpdateArgs(BaseModel):
    record_id: str
    fields: dict[str, Any] = {}


class MockSheetsUpdateTool(Tool):
    name = "sheets.update"
    description = "Update fields on an existing candidate record by record_id."
    input_model = SheetsUpdateArgs

    async def run(self, arguments: SheetsUpdateArgs) -> ToolResult:
        _seed()
        record = _tracker.get(arguments.record_id)
        if not record:
            return ToolResult(success=False, error=f"record '{arguments.record_id}' not found")
        record.update(arguments.fields)
        return ToolResult(success=True, data={"record_id": arguments.record_id, "record": record})
