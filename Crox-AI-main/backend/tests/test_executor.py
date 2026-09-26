from agent.events import EventEmitter
from agent.executor import Executor
from agent.state import AgentStateManager
from models.schemas import ToolCall, WorkflowPlan, WorkflowStep
from tests.fakes import FakeEventRepository, FakeStateRepository


def _manager() -> AgentStateManager:
    plan = WorkflowPlan(goal="g", steps=[WorkflowStep(id="find_candidate", objective="find candidate")])
    return AgentStateManager.new("run-exec", "g", plan, repository=FakeStateRepository())


async def test_execute_unknown_tool_returns_failure_without_crashing():
    manager = _manager()
    emitter = EventEmitter("run-exec", repository=FakeEventRepository())
    result = await Executor().execute(ToolCall(tool="shell.execute", arguments={}), manager, emitter)

    assert not result.success
    assert "unknown tool" in result.error
    assert manager.state.execution_history[-1].tool == "shell.execute"


async def test_execute_invalid_arguments_returns_failure():
    manager = _manager()
    emitter = EventEmitter("run-exec", repository=FakeEventRepository())
    # sheets.insert requires name+email; omit both.
    result = await Executor().execute(ToolCall(tool="sheets.insert", arguments={}), manager, emitter)

    assert not result.success
    assert "invalid arguments" in result.error


async def test_execute_valid_tool_call_updates_state_and_emits_events():
    manager = _manager()
    events = FakeEventRepository()
    emitter = EventEmitter("run-exec", repository=events)

    result = await Executor().execute(
        ToolCall(tool="sheets.search", arguments={"email": "rahul.sharma@example.com"}), manager, emitter
    )

    assert result.success
    assert result.data["found"] is True
    assert manager.state.last_result.tool == "sheets.search"

    event_types = [e["event_type"] for e in events.list_for_run("run-exec")]
    assert "TOOL_CALLED" in event_types
    assert "TOOL_RESULT" in event_types
