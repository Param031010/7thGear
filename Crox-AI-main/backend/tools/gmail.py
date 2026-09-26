"""Real Gmail API tools, backed by the OAuth flow in
integrations/google_oauth.py. Resume attachments are uploaded straight to
Supabase Storage (see integrations/supabase_storage.py) rather than kept as
local files, so sheets.py can store a durable URL instead of a local path.
"""

import base64
from functools import lru_cache
from typing import Any, Optional

from pydantic import BaseModel

from integrations.google_oauth import get_google_credentials
from integrations.supabase_storage import upload_resume
from models.schemas import ToolResult
from tools.base import Tool


@lru_cache
def _gmail_service():
    from googleapiclient.discovery import build

    return build("gmail", "v1", credentials=get_google_credentials())


def _header(headers: list[dict], name: str) -> str:
    return next((h["value"] for h in headers if h["name"].lower() == name.lower()), "")


def _walk_parts(payload: dict) -> list[dict]:
    """Flattens the (possibly nested multipart) MIME tree into a flat list of parts."""
    parts = [payload]
    for part in payload.get("parts", []) or []:
        parts.extend(_walk_parts(part))
    return parts


def _extract_body(payload: dict) -> str:
    for part in _walk_parts(payload):
        if part.get("mimeType") == "text/plain" and part.get("body", {}).get("data"):
            return base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8", errors="replace")
    # Fall back to the first part with any body data (e.g. text/html) if no plain-text part exists.
    for part in _walk_parts(payload):
        if part.get("body", {}).get("data"):
            return base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8", errors="replace")
    return ""


def _find_attachment(payload: dict) -> Optional[dict]:
    for part in _walk_parts(payload):
        filename = part.get("filename")
        attachment_id = part.get("body", {}).get("attachmentId")
        if filename and attachment_id:
            return {"filename": filename, "attachment_id": attachment_id, "mime_type": part.get("mimeType", "")}
    return None


class GmailSearchArgs(BaseModel):
    query: str = "internship application"
    max_results: int = 10


class GmailSearchTool(Tool):
    name = "gmail.search"
    description = "Search Gmail for messages matching a query. Each result has a message_id field to pass to gmail.read / gmail.download_attachment."
    input_model = GmailSearchArgs

    async def run(self, arguments: GmailSearchArgs) -> ToolResult:
        try:
            service = _gmail_service()
            listing = (
                service.users()
                .messages()
                .list(userId="me", q=arguments.query, maxResults=arguments.max_results)
                .execute()
            )
            messages: list[dict[str, Any]] = []
            for item in listing.get("messages", []):
                full = (
                    service.users()
                    .messages()
                    .get(userId="me", id=item["id"], format="metadata", metadataHeaders=["From", "Subject"])
                    .execute()
                )
                headers = full.get("payload", {}).get("headers", [])
                messages.append(
                    {
                        "message_id": full["id"],
                        "from": _header(headers, "From"),
                        "subject": _header(headers, "Subject"),
                        "snippet": full.get("snippet", ""),
                    }
                )
        except Exception as exc:  # noqa: BLE001
            return ToolResult(success=False, error=str(exc))
        return ToolResult(success=True, data={"messages": messages})


class GmailReadArgs(BaseModel):
    message_id: str


class GmailReadTool(Tool):
    name = "gmail.read"
    description = "Read the full content of a Gmail message by id, including any attachment filename."
    input_model = GmailReadArgs

    async def run(self, arguments: GmailReadArgs) -> ToolResult:
        try:
            service = _gmail_service()
            message = service.users().messages().get(userId="me", id=arguments.message_id, format="full").execute()
            payload = message.get("payload", {})
            headers = payload.get("headers", [])
            attachment = _find_attachment(payload)
        except Exception as exc:  # noqa: BLE001
            return ToolResult(success=False, error=str(exc))

        return ToolResult(
            success=True,
            data={
                "message_id": message["id"],
                "from": _header(headers, "From"),
                "subject": _header(headers, "Subject"),
                "snippet": message.get("snippet", ""),
                "body": _extract_body(payload),
                "attachment": attachment["filename"] if attachment else None,
            },
        )


class GmailDownloadAttachmentArgs(BaseModel):
    message_id: str


class GmailDownloadAttachmentTool(Tool):
    name = "gmail.download_attachment"
    description = (
        "Download the resume attachment for a message and upload it to Supabase Storage. "
        "Returns a local file_path (for document extraction) and a durable storage_url."
    )
    input_model = GmailDownloadAttachmentArgs

    async def run(self, arguments: GmailDownloadAttachmentArgs) -> ToolResult:
        try:
            service = _gmail_service()
            message = (
                service.users().messages().get(userId="me", id=arguments.message_id, format="full").execute()
            )
            attachment = _find_attachment(message.get("payload", {}))
            if not attachment:
                return ToolResult(success=False, error="message has no attachment")

            raw = (
                service.users()
                .messages()
                .attachments()
                .get(userId="me", messageId=arguments.message_id, id=attachment["attachment_id"])
                .execute()
            )
            content = base64.urlsafe_b64decode(raw["data"])

            import tempfile
            from pathlib import Path

            local_path = Path(tempfile.gettempdir()) / "workflowos_attachments" / arguments.message_id / attachment["filename"]
            local_path.parent.mkdir(parents=True, exist_ok=True)
            local_path.write_bytes(content)

            storage_url = upload_resume(
                f"{arguments.message_id}/{attachment['filename']}",
                content,
                content_type=attachment["mime_type"] or "application/octet-stream",
            )
        except Exception as exc:  # noqa: BLE001
            return ToolResult(success=False, error=str(exc))

        return ToolResult(success=True, data={"file_path": str(local_path), "storage_url": storage_url})
