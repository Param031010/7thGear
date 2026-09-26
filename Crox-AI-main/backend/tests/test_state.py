from agent.state import AgentStateManager
from models.schemas import ToolResult, WorkflowPlan, WorkflowStep
from tests.fakes import FakeStateRepository


def _plan() -> WorkflowPlan:
    return WorkflowPlan(
        goal="test goal",
        steps=[WorkflowStep(id="a", objective="do a"), WorkflowStep(id="b", objective="do b")],
    )


def test_new_state_persists_immediately():
    repo = FakeStateRepository()
    AgentStateManager.new("run-1", "test goal", _plan(), repository=repo)
    assert repo.get("run-1") is not None


def test_record_tool_call_updates_history_and_last_result():
    repo = FakeStateRepository()
    manager = AgentStateManager.new("run-2", "g", _plan(), repository=repo)
    result = ToolResult(success=True, data={"found": True})
    manager.record_tool_call("sheets.search", {"email": "a@b.com"}, result, reason="checking tracker")

    assert len(manager.state.execution_history) == 1
    assert manager.state.last_result.tool == "sheets.search"
    assert manager.state.last_result.success is True


def test_mark_completed_and_update_facts():
    repo = FakeStateRepository()
    manager = AgentStateManager.new("run-3", "g", _plan(), repository=repo)
    manager.mark_completed("a")
    manager.update_facts({"candidate_name": "Rahul"})

    assert "a" in manager.state.completed_objectives
    assert manager.state.facts["candidate_name"] == "Rahul"


def test_load_reconstructs_equivalent_state_after_restart():
    repo = FakeStateRepository()
    original = AgentStateManager.new("run-4", "test goal", _plan(), repository=repo)
    original.update_facts({"candidate_email": "rahul@example.com"})
    original.mark_completed("a")

    # Simulate a backend restart: a brand new manager loaded purely from the
    # repository, with no reference to the original in-memory object.
    reloaded = AgentStateManager.load("run-4", repo)

    assert reloaded is not None
    assert reloaded.state.goal == original.state.goal
    assert reloaded.state.facts == original.state.facts
    assert reloaded.state.completed_objectives == original.state.completed_objectives


def test_load_returns_none_for_unknown_run():
    repo = FakeStateRepository()
    assert AgentStateManager.load("no-such-run", repo) is None
