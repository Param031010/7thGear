from pathlib import Path

import agent.gemini_client
from tools.document import DocumentExtractFieldsTool, DocumentExtractTextTool, ExtractFieldsArgs, ExtractTextArgs

FIXTURE = Path(__file__).resolve().parent.parent / "fixtures" / "resumes" / "rahul_sharma.txt"


async def test_extract_text_reads_txt_fixture():
    result = await DocumentExtractTextTool().run(ExtractTextArgs(file_path=str(FIXTURE)))
    assert result.success
    assert "rahul.sharma@example.com" in result.data["text"]


async def test_extract_text_missing_file_fails_cleanly():
    result = await DocumentExtractTextTool().run(ExtractTextArgs(file_path="does/not/exist.pdf"))
    assert not result.success


async def test_extract_fields_falls_back_to_regex_when_gemini_unavailable(monkeypatch):
    # Force the Gemini path to fail regardless of whether a real
    # GEMINI_API_KEY is configured in .env, so this deterministically
    # exercises the offline regex fallback rather than making a real network
    # call in the test suite.
    async def fake_extract_structured_fields(text: str):
        raise RuntimeError("simulated Gemini outage")

    monkeypatch.setattr(agent.gemini_client, "extract_structured_fields", fake_extract_structured_fields)

    result = await DocumentExtractFieldsTool().run(ExtractFieldsArgs(file_path=str(FIXTURE)))
    assert result.success
    assert result.data["email"] == "rahul.sharma@example.com"
    assert "Python" in result.data["skills"]


async def test_extract_fields_uses_gemini_when_available(monkeypatch):
    async def fake_extract_structured_fields(text: str):
        return {"name": "Rahul Sharma", "email": "from-gemini@example.com", "phone": "", "college": "", "skills": ["Go"]}

    monkeypatch.setattr(agent.gemini_client, "extract_structured_fields", fake_extract_structured_fields)

    result = await DocumentExtractFieldsTool().run(ExtractFieldsArgs(file_path=str(FIXTURE)))
    assert result.success
    assert result.data["email"] == "from-gemini@example.com"
    assert result.data["skills"] == ["Go"]
