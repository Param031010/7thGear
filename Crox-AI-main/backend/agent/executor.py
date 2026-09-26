from agent.events import EventEmitter
from agent.state import AgentStateManager
from models.schemas import EventType, ToolCall, ToolResult
from tools.base import ToolArgumentError
from tools.registry import get_tool


class Executor:
    """The only place a tool actually runs. Gemini never gets closer to the
    system than producing a ToolCall (tool name + arguments); this validates
    both against the registered tool's schema before anything executes.
    """

    async def execute(
        self,
        tool_call: ToolCall,
        state_manager: AgentStateManager,
        emitter: EventEmitter,
    ) -> ToolResult:
        tool = get_tool(tool_call.tool)
        if tool is None:
            result = ToolResult(success=False, error=f"unknown tool '{tool_call.tool}'")
            await emitter.emit(
                EventType.TOOL_RESULT, tool_name=tool_call.tool, status="error", error=result.error
            )
            state_manager.record_tool_call(tool_call.tool, tool_call.arguments, result)
            return result

        await emitter.emit(EventType.TOOL_CALLED, tool_name=tool_call.tool, input=tool_call.arguments)

        try:
            validated_args = tool.validate_arguments(tool_call.arguments)
        except ToolArgumentError as exc:
            result = ToolResult(success=False, error=f"invalid arguments: {exc}")
        else:
            try:
                result = await tool.run(validated_args)
            except Exception as exc:  # noqa: BLE001 - a tool crash becomes a failed result, not a dead run
                result = ToolResult(success=False, error=str(exc))

        state_manager.record_tool_call(tool_call.tool, tool_call.arguments, result)
        await emitter.emit(
            EventType.TOOL_RESULT,
            tool_name=tool_call.tool,
            output=result.data,
            status="success" if result.success else "error",
            error=result.error,
        )
        return result
