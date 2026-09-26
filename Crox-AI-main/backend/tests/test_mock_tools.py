import pytest

from tools.mock.mock_gmail import (
    GmailDownloadAttachmentArgs,
    GmailReadArgs,
    GmailSearchArgs,
    MockGmailDownloadAttachmentTool,
    MockGmailReadTool,
    MockGmailSearchTool,
)
from tools.mock.mock_sheets import (
    MockSheetsInsertTool,
    MockSheetsSearchTool,
    MockSheetsUpdateTool,
    SheetsInsertArgs,
    SheetsSearchArgs,
    SheetsUpdateArgs,
)
from tools.mock.mock_slack import MockSlackSendTool, SlackSendArgs, sent_messages


async def test_gmail_search_returns_fixture_messages():
    result = await MockGmailSearchTool().run(GmailSearchArgs())
    assert result.success
    ids = {m["message_id"] for m in result.data["messages"]}
    assert {"msg_priya", "msg_rahul"} <= ids


async def test_gmail_read_unknown_message_fails():
    result = await MockGmailReadTool().run(GmailReadArgs(message_id="does_not_exist"))
    assert not result.success


async def test_gmail_download_attachment_returns_real_path():
    result = await MockGmailDownloadAttachmentTool().run(GmailDownloadAttachmentArgs(message_id="msg_rahul"))
    assert result.success
    assert result.data["file_path"].endswith("rahul_sharma.txt")


async def test_sheets_search_finds_seeded_candidate():
    result = await MockSheetsSearchTool().run(SheetsSearchArgs(email="rahul.sharma@example.com"))
    assert result.data["found"] is True
    assert result.data["record_id"] == "C1024"


async def test_sheets_search_no_match_for_new_candidate():
    result = await MockSheetsSearchTool().run(SheetsSearchArgs(email="priya.patel@example.com"))
    assert result.data["found"] is False


async def test_sheets_insert_creates_new_record():
    result = await MockSheetsInsertTool().run(
        SheetsInsertArgs(name="Priya Patel", email="priya.patel@example.com", skills=["Python"])
    )
    assert result.success
    assert result.data["record_id"] != "C1024"


async def test_sheets_insert_rejects_duplicate_email():
    result = await MockSheetsInsertTool().run(
        SheetsInsertArgs(name="Rahul Sharma", email="rahul.sharma@example.com")
    )
    assert not result.success
    assert "already exists" in result.error


async def test_sheets_update_mutates_existing_record():
    result = await MockSheetsUpdateTool().run(SheetsUpdateArgs(record_id="C1024", fields={"status": "shortlisted"}))
    assert result.success
    assert result.data["record"]["status"] == "shortlisted"


async def test_sheets_update_unknown_record_fails():
    result = await MockSheetsUpdateTool().run(SheetsUpdateArgs(record_id="C9999", fields={}))
    assert not result.success


async def test_slack_send_records_message():
    result = await MockSlackSendTool().run(SlackSendArgs(text="hello team"))
    assert result.success
    assert sent_messages[-1]["text"] == "hello team"
