from pydantic import BaseModel

from models.schemas import ToolResult
from tools.base import Tool

CHANNEL = "all-legend"

# In-memory log of sent messages, useful for tests/inspection during DEMO_MODE.
sent_messages: list[dict[str, str]] = []


class SlackSendArgs(BaseModel):
    text: str


class MockSlackSendTool(Tool):
    name = "slack.send"
    description = "Send a message to the hiring team's Slack channel. Takes only a 'text' argument -- the channel is fixed."
    input_model = SlackSendArgs

    async def run(self, arguments: SlackSendArgs) -> ToolResult:
        sent_messages.append({"channel": CHANNEL, "text": arguments.text})
        return ToolResult(success=True, data={"channel": CHANNEL, "text": arguments.text})
