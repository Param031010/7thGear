import re
from pathlib import Path

from pydantic import BaseModel

from models.schemas import ToolResult
from tools.base import Tool


def _read_any(file_path: str) -> str:
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(file_path)
    if path.suffix.lower() == ".pdf":
        import fitz  # PyMuPDF

        doc = fitz.open(path)
        try:
            return "\n".join(page.get_text() for page in doc)
        finally:
            doc.close()
    return path.read_text(encoding="utf-8")


class ExtractTextArgs(BaseModel):
    file_path: str


class DocumentExtractTextTool(Tool):
    name = "document.extract_text"
    description = "Extract raw text from a PDF or text file at a local path."
    input_model = ExtractTextArgs

    async def run(self, arguments: ExtractTextArgs) -> ToolResult:
        try:
            text = _read_any(arguments.file_path)
        except FileNotFoundError:
            return ToolResult(success=False, error=f"file not found: {arguments.file_path}")
        return ToolResult(success=True, data={"text": text})


class ExtractFieldsArgs(BaseModel):
    file_path: str


_EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
_PHONE_RE = re.compile(r"\+?\d[\d\-\s]{7,}\d")


def _regex_extract_fields(text: str) -> dict:
    """Deterministic fallback used when no Gemini key is configured, so the
    tool still works offline / in tests without a network call."""
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    name = lines[0] if lines else ""
    email_match = _EMAIL_RE.search(text)
    phone_match = _PHONE_RE.search(text)
    college_match = re.search(r"College:\s*(.+)", text)
    skills_match = re.search(r"SKILLS\s*\n(.+)", text)
    skills: list[str] = []
    if skills_match:
        skills = [s.strip() for s in skills_match.group(1).split(",") if s.strip()]
    return {
        "name": name.title() if name.isupper() else name,
        "email": email_match.group(0) if email_match else "",
        "phone": phone_match.group(0) if phone_match else "",
        "college": college_match.group(1).strip() if college_match else "",
        "skills": skills,
    }


class DocumentExtractFieldsTool(Tool):
    name = "document.extract_fields"
    description = (
        "Extract structured candidate fields (name, email, phone, college, skills) "
        "from a resume file at a local path."
    )
    input_model = ExtractFieldsArgs

    async def run(self, arguments: ExtractFieldsArgs) -> ToolResult:
        try:
            text = _read_any(arguments.file_path)
        except FileNotFoundError:
            return ToolResult(success=False, error=f"file not found: {arguments.file_path}")

        try:
            from agent.gemini_client import extract_structured_fields

            fields = await extract_structured_fields(text)
        except Exception:
            fields = _regex_extract_fields(text)

        return ToolResult(success=True, data=fields)
