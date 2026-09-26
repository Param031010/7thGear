"""Real Google Sheets API tools. The candidate tracker sheet is created
automatically on first use (and its id cached locally) unless
GOOGLE_SHEETS_SPREADSHEET_ID pins an existing one -- nobody has to go create
a sheet by hand first.
"""

from functools import lru_cache
from pathlib import Path
from typing import Any, Optional

from pydantic import BaseModel, field_validator

from config import get_settings
from integrations.google_oauth import get_google_credentials
from models.schemas import ToolResult
from tools.base import Tool

HEADERS = ["record_id", "name", "email", "phone", "college", "skills", "status", "resume_url"]


@lru_cache
def _sheets_service():
    from googleapiclient.discovery import build

    return build("sheets", "v4", credentials=get_google_credentials())


@lru_cache
def _spreadsheet_id() -> str:
    settings = get_settings()
    if settings.google_sheets_spreadsheet_id:
        return settings.google_sheets_spreadsheet_id

    cache_path = Path(settings.google_sheets_id_cache)
    if cache_path.exists():
        return cache_path.read_text().strip()

    service = _sheets_service()
    created = service.spreadsheets().create(
        body={"properties": {"title": "WorkFlowOS Candidate Tracker"}}
    ).execute()
    spreadsheet_id = created["spreadsheetId"]

    service.spreadsheets().values().update(
        spreadsheetId=spreadsheet_id,
        range=f"{settings.google_sheets_tab_name}!A1:H1",
        valueInputOption="RAW",
        body={"values": [HEADERS]},
    ).execute()

    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(spreadsheet_id)
    return spreadsheet_id


def _coerce_skills(value: Any) -> list[str]:
    """The model sometimes hands back skills as a comma-separated string
    instead of a list, despite the schema saying list[str] -- normalize
    either shape here so a malformed argument can't silently corrupt the
    sheet (join()-ing a string splits it into individual characters)."""
    if isinstance(value, list):
        return [str(v).strip() for v in value if str(v).strip()]
    if isinstance(value, str):
        return [s.strip() for s in value.split(",") if s.strip()]
    return []


def _row_to_record(row: list[str]) -> dict[str, Any]:
    padded = row + [""] * (len(HEADERS) - len(row))
    record = dict(zip(HEADERS, padded))
    record["skills"] = _coerce_skills(record["skills"])
    return record


def _record_to_row(record: dict[str, Any]) -> list[str]:
    row = dict(record)
    row["skills"] = ", ".join(_coerce_skills(row.get("skills", [])))
    return [str(row.get(h, "")) for h in HEADERS]


def _read_all_rows() -> list[list[str]]:
    settings = get_settings()
    service = _sheets_service()
    result = (
        service.spreadsheets()
        .values()
        .get(spreadsheetId=_spreadsheet_id(), range=f"{settings.google_sheets_tab_name}!A2:H")
        .execute()
    )
    return result.get("values", [])


class SheetsSearchArgs(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None


class SheetsSearchTool(Tool):
    name = "sheets.search"
    description = "Search the candidate tracker sheet by name or email. Returns whether a matching record exists."
    input_model = SheetsSearchArgs

    async def run(self, arguments: SheetsSearchArgs) -> ToolResult:
        try:
            rows = _read_all_rows()
        except Exception as exc:  # noqa: BLE001
            return ToolResult(success=False, error=str(exc))

        for row in rows:
            record = _row_to_record(row)
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
    resume_url: str = ""

    @field_validator("skills", mode="before")
    @classmethod
    def _normalize_skills(cls, v: Any) -> list[str]:
        return _coerce_skills(v)


class SheetsInsertTool(Tool):
    name = "sheets.insert"
    description = (
        "Insert a new candidate row into the tracker sheet. Only call this when sheets.search found no match. "
        "'skills' must be a JSON array of strings, e.g. [\"Python\", \"SQL\"] -- not a comma-separated string."
    )
    input_model = SheetsInsertArgs

    async def run(self, arguments: SheetsInsertArgs) -> ToolResult:
        settings = get_settings()
        try:
            rows = _read_all_rows()
            for row in rows:
                if _row_to_record(row).get("email") == arguments.email:
                    return ToolResult(
                        success=False,
                        error=f"candidate with email {arguments.email} already exists as {row[0]}",
                    )

            record_id = f"C{1024 + len(rows) + 1}"
            record = {
                "record_id": record_id,
                "name": arguments.name,
                "email": arguments.email,
                "phone": arguments.phone,
                "college": arguments.college,
                "skills": arguments.skills,
                "status": "applied",
                "resume_url": arguments.resume_url,
            }

            service = _sheets_service()
            service.spreadsheets().values().append(
                spreadsheetId=_spreadsheet_id(),
                range=f"{settings.google_sheets_tab_name}!A:H",
                valueInputOption="RAW",
                insertDataOption="INSERT_ROWS",
                body={"values": [_record_to_row(record)]},
            ).execute()
        except Exception as exc:  # noqa: BLE001
            return ToolResult(success=False, error=str(exc))

        return ToolResult(success=True, data={"record_id": record_id, "record": record})


class SheetsUpdateArgs(BaseModel):
    record_id: str
    fields: dict[str, Any] = {}


class SheetsUpdateTool(Tool):
    name = "sheets.update"
    description = "Update fields on an existing candidate row by record_id."
    input_model = SheetsUpdateArgs

    async def run(self, arguments: SheetsUpdateArgs) -> ToolResult:
        settings = get_settings()
        try:
            rows = _read_all_rows()
            row_index = next((i for i, r in enumerate(rows) if r and r[0] == arguments.record_id), None)
            if row_index is None:
                return ToolResult(success=False, error=f"record '{arguments.record_id}' not found")

            record = _row_to_record(rows[row_index])
            record.update(arguments.fields)

            service = _sheets_service()
            sheet_row = row_index + 2  # +1 for header, +1 for 1-indexing
            service.spreadsheets().values().update(
                spreadsheetId=_spreadsheet_id(),
                range=f"{settings.google_sheets_tab_name}!A{sheet_row}:H{sheet_row}",
                valueInputOption="RAW",
                body={"values": [_record_to_row(record)]},
            ).execute()
        except Exception as exc:  # noqa: BLE001
            return ToolResult(success=False, error=str(exc))

        return ToolResult(success=True, data={"record_id": arguments.record_id, "record": record})
