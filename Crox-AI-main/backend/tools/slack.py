"""Real Slack Web API tool, backed by SLACK_BOT_TOKEN. The bot must be a
member of the target channel (invite it with `/invite @your-bot-name` in
Slack) or chat.postMessage will fail with `not_in_channel`.

The channel is hardcoded rather than left for Gemini to choose -- it kept
guessing plausible-but-wrong names (e.g. 'hiring-team') that don't exist in
the workspace, triggering unnecessary replanning/ask-user detours.
"""

from functools import lru_cache

from pydantic import BaseModel

from config import get_settings
from models.schemas import ToolResult
from tools.base import Tool

CHANNEL = "all-legend"


class SlackNotConfigured(RuntimeError):
    pass


@lru_cache
def _slack_client():
    settings = get_settings()
    if not settings.slack_bot_token:
        raise SlackNotConfigured("SLACK_BOT_TOKEN is not set in .env")

    from slack_sdk.web.async_client import AsyncWebClient

    return AsyncWebClient(token=settings.slack_bot_token)


class SlackSendArgs(BaseModel):
    text: str


class SlackSendTool(Tool):
    name = "slack.send"
    description = "Send a message to the hiring team's Slack channel. Takes only a 'text' argument -- the channel is fixed."
    input_model = SlackSendArgs

    async def run(self, arguments: SlackSendArgs) -> ToolResult:
        try:
            client = _slack_client()
            response = await client.chat_postMessage(channel=CHANNEL, text=arguments.text)
        except Exception as exc:  # noqa: BLE001 - SlackApiError and SlackNotConfigured both land here
            return ToolResult(success=False, error=str(exc))

        return ToolResult(
            success=True,
            data={"channel": response.get("channel", CHANNEL), "ts": response.get("ts"), "text": arguments.text},
        )
