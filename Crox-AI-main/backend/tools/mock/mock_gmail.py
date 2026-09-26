import json
from pathlib import Path
from typing import Optional

from pydantic import BaseModel

from models.schemas import ToolResult
from tools.base import Tool

FIXTURES_DIR = Path(__file__).resolve().parent.parent.parent / "fixtures"


def _load_inbox() -> list[dict]:
    with open(FIXTURES_DIR / "gmail_inbox.json", encoding="utf-8") as f:
        return json.load(f)["messages"]


class GmailSearchArgs(BaseModel):
    query: str = "internship application"
    max_results: int = 10


class MockGmailSearchTool(Tool):
    name = "gmail.search"
    description = "Search the hiring inbox for messages matching a query. Each result has a message_id field to pass to gmail.read / gmail.download_attachment."
    input_model = GmailSearchArgs

    async def run(self, arguments: GmailSearchArgs) -> ToolResult:
        messages = _load_inbox()
        results = [
            {"message_id": m["id"], "from": m["from"], "subject": m["subject"], "snippet": m["snippet"]}
            for m in messages
        ]
        return ToolResult(success=True, data={"messages": results[: arguments.max_results]})


class GmailReadArgs(BaseModel):
    message_id: str


class MockGmailReadTool(Tool):
    name = "gmail.read"
    description = "Read the full content of a message by id, including any attachment filename."
    input_model = GmailReadArgs

    async def run(self, arguments: GmailReadArgs) -> ToolResult:
        messages = _load_inbox()
        match = next((m for m in messages if m["id"] == arguments.message_id), None)
        if not match:
            return ToolResult(success=False, error=f"message '{arguments.message_id}' not found")
        data = {k: v for k, v in match.items() if k != "id"}
        data["message_id"] = match["id"]
        return ToolResult(success=True, data=data)


class GmailDownloadAttachmentArgs(BaseModel):
    message_id: str


class MockGmailDownloadAttachmentTool(Tool):
    name = "gmail.download_attachment"
    description = "Download the resume attachment for a message and return a local file path."
    input_model = GmailDownloadAttachmentArgs

    async def run(self, arguments: GmailDownloadAttachmentArgs) -> ToolResult:
        messages = _load_inbox()
        match = next((m for m in messages if m["id"] == arguments.message_id), None)
        if not match:
            return ToolResult(success=False, error=f"message '{arguments.message_id}' not found")
        attachment: Optional[str] = match.get("attachment")
        if not attachment:
            return ToolResult(success=False, error="message has no attachment")
        path = FIXTURES_DIR / "resumes" / attachment
        return ToolResult(success=True, data={"file_path": str(path)})
