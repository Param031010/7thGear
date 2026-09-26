from functools import lru_cache

from config import get_settings
from tools.base import Tool
from tools.desktop import (
    DesktopClickTool,
    DesktopGetWindowTool,
    DesktopHotkeyTool,
    DesktopOpenAppTool,
    DesktopTypeTool,
)
from tools.document import DocumentExtractFieldsTool, DocumentExtractTextTool
from tools.user import AskUserTool


@lru_cache
def get_tool_registry() -> dict[str, Tool]:
    settings = get_settings()

    if settings.demo_mode:
        from tools.mock.mock_gmail import (
            MockGmailDownloadAttachmentTool,
            MockGmailReadTool,
            MockGmailSearchTool,
        )
        from tools.mock.mock_sheets import (
            MockSheetsInsertTool,
            MockSheetsSearchTool,
            MockSheetsUpdateTool,
        )
        from tools.mock.mock_slack import MockSlackSendTool

        gmail_search, gmail_read, gmail_download = (
            MockGmailSearchTool(),
            MockGmailReadTool(),
            MockGmailDownloadAttachmentTool(),
        )
        sheets_search, sheets_insert, sheets_update = (
            MockSheetsSearchTool(),
            MockSheetsInsertTool(),
            MockSheetsUpdateTool(),
        )
        slack_send = MockSlackSendTool()
    else:
        from tools.gmail import GmailDownloadAttachmentTool, GmailReadTool, GmailSearchTool
        from tools.sheets import SheetsInsertTool, SheetsSearchTool, SheetsUpdateTool
        from tools.slack import SlackSendTool

        gmail_search, gmail_read, gmail_download = GmailSearchTool(), GmailReadTool(), GmailDownloadAttachmentTool()
        sheets_search, sheets_insert, sheets_update = SheetsSearchTool(), SheetsInsertTool(), SheetsUpdateTool()
        slack_send = SlackSendTool()

    from tools.browser import BrowserClickTool, BrowserGetTextTool, BrowserNavigateTool, BrowserTypeTool

    tools: list[Tool] = [
        gmail_search,
        gmail_read,
        gmail_download,
        sheets_search,
        sheets_insert,
        sheets_update,
        slack_send,
        BrowserNavigateTool(),
        BrowserClickTool(),
        BrowserTypeTool(),
        BrowserGetTextTool(),
        DesktopOpenAppTool(),
        DesktopGetWindowTool(),
        DesktopClickTool(),
        DesktopTypeTool(),
        DesktopHotkeyTool(),
        DocumentExtractTextTool(),
        DocumentExtractFieldsTool(),
        AskUserTool(),
    ]
    return {tool.name: tool for tool in tools}


def get_tool(name: str) -> Tool | None:
    return get_tool_registry().get(name)


def list_tool_specs() -> list[dict]:
    return [tool.spec() for tool in get_tool_registry().values()]
