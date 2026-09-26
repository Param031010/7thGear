from agent import orchestrator
from agent.state import AgentStateManager
from models.schemas import AgentAction, ReplanDecisionType, RunStatus, ToolCall, WorkflowPlan, WorkflowStep
from tests.fakes import FakeApprovalRepository, FakeEventRepository, FakeRunRepository, FakeStateRepository


def _emitter(run_id, events):
    from agent.events import EventEmitter

    return EventEmitter(run_id, repository=events)


async def test_run_loop_completes_when_decision_is_complete(monkeypatch):
    run_repo = FakeRunRepository()
    approval_repo = FakeApprovalRepository()
    events = FakeEventRepository()
    run = run_repo.create(None, "goal")

    plan = WorkflowPlan(goal="goal", steps=[WorkflowStep(id="a", objective="do a")])
    manager = AgentStateManager.new(run["id"], "goal", plan, repository=FakeStateRepository())

    async def fake_decide(state_manager):
        return AgentAction(decision=ReplanDecisionType.COMPLETE, reason="done")

    monkeypatch.setattr(orchestrator, "decide_next_action", fake_decide)
    monkeypatch.setattr(orchestrator, "EventEmitter", lambda rid: _emitter(rid, events))

    await orchestrator.run_loop(run["id"], manager, run_repo, approval_repo)

    assert run_repo.get(run["id"])["status"] == RunStatus.COMPLETED.value
    assert any(e["event_type"] == "WORKFLOW_COMPLETED" for e in events.list_for_run(run["id"]))


async def test_run_loop_fails_when_decision_is_fail(monkeypatch):
    run_repo = FakeRunRepository()
    approval_repo = FakeApprovalRepository()
    events = FakeEventRepository()
    run = run_repo.create(None, "goal")
    plan = WorkflowPlan(goal="goal", steps=[WorkflowStep(id="a", objective="do a")])
    manager = AgentStateManager.new(run["id"], "goal", plan, repository=FakeStateRepository())

    async def fake_decide(state_manager):
        return AgentAction(decision=ReplanDecisionType.FAIL, reason="cannot proceed")

    monkeypatch.setattr(orchestrator, "decide_next_action", fake_decide)
    monkeypatch.setattr(orchestrator, "EventEmitter", lambda rid: _emitter(rid, events))

    await orchestrator.run_loop(run["id"], manager, run_repo, approval_repo)

    assert run_repo.get(run["id"])["status"] == RunStatus.FAILED.value
    assert any(e["event_type"] == "WORKFLOW_FAILED" for e in events.list_for_run(run["id"]))


async def test_run_loop_pauses_and_creates_approval_on_ask_user(monkeypatch):
    run_repo = FakeRunRepository()
    approval_repo = FakeApprovalRepository()
    events = FakeEventRepository()
    run = run_repo.create(None, "goal")
    plan = WorkflowPlan(goal="goal", steps=[WorkflowStep(id="a", objective="do a")])
    manager = AgentStateManager.new(run["id"], "goal", plan, repository=FakeStateRepository())

    async def fake_decide(state_manager):
        return AgentAction(
            decision=ReplanDecisionType.ASK_USER,
            reason="ambiguous match",
            ask_user_question="Which candidate did you mean?",
            ask_user_options=["C1024", "C1089"],
        )

    monkeypatch.setattr(orchestrator, "decide_next_action", fake_decide)
    monkeypatch.setattr(orchestrator, "EventEmitter", lambda rid: _emitter(rid, events))

    await orchestrator.run_loop(run["id"], manager, run_repo, approval_repo)

    assert run_repo.get(run["id"])["status"] == RunStatus.AWAITING_USER_INPUT.value
    pending = approval_repo.latest_pending_for_run(run["id"], "user_input")
    assert pending is not None
    assert any(e["event_type"] == "USER_INPUT_REQUIRED" for e in events.list_for_run(run["id"]))


async def test_run_loop_falls_back_to_ask_user_when_continue_has_no_next_action(monkeypatch):
    """Reproduces a real failure seen in production: the model explained (in
    `reason`) that it wanted to ask the user something -- e.g. the Slack
    channel it tried doesn't exist -- but left `decision` as CONTINUE and
    `next_action` empty instead of setting ASK_USER. The run must pause and
    ask, not hard-fail."""
    run_repo = FakeRunRepository()
    approval_repo = FakeApprovalRepository()
    events = FakeEventRepository()
    run = run_repo.create(None, "goal")
    plan = WorkflowPlan(goal="goal", steps=[WorkflowStep(id="a", objective="do a")])
    manager = AgentStateManager.new(run["id"], "goal", plan, repository=FakeStateRepository())

    async def fake_decide(state_manager):
        return AgentAction(
            decision=ReplanDecisionType.CONTINUE,
            reason="The 'hiring-team' Slack channel was not found. Asking the user for the correct channel.",
        )

    monkeypatch.setattr(orchestrator, "decide_next_action", fake_decide)
    monkeypatch.setattr(orchestrator, "EventEmitter", lambda rid: _emitter(rid, events))

    await orchestrator.run_loop(run["id"], manager, run_repo, approval_repo)

    assert run_repo.get(run["id"])["status"] == RunStatus.AWAITING_USER_INPUT.value
    assert approval_repo.latest_pending_for_run(run["id"], "user_input") is not None
    event_types = [e["event_type"] for e in events.list_for_run(run["id"])]
    assert "USER_INPUT_REQUIRED" in event_types
    assert "WORKFLOW_FAILED" not in event_types


async def test_run_loop_executes_real_tool_calls_end_to_end(monkeypatch):
    """CONTINUE decisions really run the mock tool through the Executor,
    not just simulated state changes."""
    run_repo = FakeRunRepository()
    approval_repo = FakeApprovalRepository()
    events = FakeEventRepository()
    run = run_repo.create(None, "goal")
    plan = WorkflowPlan(goal="goal", steps=[WorkflowStep(id="check", objective="check tracker")])
    manager = AgentStateManager.new(run["id"], "goal", plan, repository=FakeStateRepository())

    calls = iter(
        [
            AgentAction(
                decision=ReplanDecisionType.CONTINUE,
                reason="checking tracker",
                current_objective="check",
                next_action=ToolCall(tool="sheets.search", arguments={"email": "rahul.sharma@example.com"}),
            ),
            AgentAction(decision=ReplanDecisionType.COMPLETE, reason="done"),
        ]
    )

    async def fake_decide(state_manager):
        return next(calls)

    monkeypatch.setattr(orchestrator, "decide_next_action", fake_decide)
    monkeypatch.setattr(orchestrator, "EventEmitter", lambda rid: _emitter(rid, events))

    await orchestrator.run_loop(run["id"], manager, run_repo, approval_repo)

    assert manager.state.last_result.data["found"] is True
    assert manager.state.execution_history[0].tool == "sheets.search"
