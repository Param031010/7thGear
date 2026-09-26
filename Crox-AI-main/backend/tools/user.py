from pydantic import BaseModel

from models.schemas import ToolResult
from tools.base import Tool


class AskUserArgs(BaseModel):
    question: str
    options: list[str] = []


class AskUserTool(Tool):
    """Invoking this tool does not itself pause anything -- the executor
    recognizes the `ask_user` tool name and pauses the run, persisting an
    `approvals` row with `approval_type='user_input'` before this runs.
    """

    name = "ask_user"
    description = "Ask the human operator a question when the agent cannot safely decide what to do next."
    input_model = AskUserArgs

    async def run(self, arguments: AskUserArgs) -> ToolResult:
        return ToolResult(success=True, data={"question": arguments.question, "options": arguments.options})
