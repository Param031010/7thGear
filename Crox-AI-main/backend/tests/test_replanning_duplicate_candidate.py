"""Section 29/34's core replanning scenario: the plan assumed a candidate
would be new, but sheets.search finds Rahul Sharma already seeded in the
tracker (fixtures/tracker_seed.json). The agent must not blindly insert a
duplicate -- it should update the existing record instead, exactly like the
spec's demo script.
"""

from agent import orchestrator
from agent.state import AgentStateManager
from models.schemas import AgentAction, ReplanDecisionType, RunStatus, ToolCall, WorkflowPlan, WorkflowStep
from tests.fakes import FakeApprovalRepository, FakeEventRepository, FakeRunRepository, FakeStateRepository
from tools.mock.mock_slack import sent_messages


def _emitter(run_id, events):
    from agent.events import EventEmitter

    return EventEmitter(run_id, repository=events)


async def test_duplicate_candidate_triggers_update_instead_of_insert(monkeypatch):
    run_repo = FakeRunRepository()
    approval_repo = FakeApprovalRepository()
    events = FakeEventRepository()
    run = run_repo.create(None, "Process internship applications")

    plan = WorkflowPlan(
        goal="Process internship applications",
        steps=[
            WorkflowStep(id="check_tracker", objective="Check candidate tracker"),
            WorkflowStep(id="update_candidate", objective="Add or update candidate"),
            WorkflowStep(id="notify_team", objective="Notify hiring team"),
        ],
    )
    manager = AgentStateManager.new(run["id"], plan.goal, plan, repository=FakeStateRepository())

    scripted = iter(
        [
            # 1. Expected path: search the tracker for the candidate from the email.
            AgentAction(
                decision=ReplanDecisionType.CONTINUE,
                reason="Looking up candidate in the tracker",
                current_objective="check_tracker",
                next_action=ToolCall(tool="sheets.search", arguments={"email": "rahul.sharma@example.com"}),
                objective_complete=True,
            ),
            # 2. Reality differs from the plan's assumption (candidate exists) ->
            #    replan to update instead of insert.
            AgentAction(
                decision=ReplanDecisionType.ALTERNATIVE_ACTION,
                reason="Candidate already exists, so updating the existing record instead of creating a duplicate.",
                current_objective="update_candidate",
                next_action=ToolCall(
                    tool="sheets.update",
                    arguments={"record_id": "C1024", "fields": {"status": "reapplied"}},
                ),
                objective_complete=True,
            ),
            # 3. Notify the team.
            AgentAction(
                decision=ReplanDecisionType.CONTINUE,
                reason="Notifying the hiring team",
                current_objective="notify_team",
                next_action=ToolCall(
                    tool="slack.send",
                    arguments={"text": "Rahul Sharma re-applied; tracker updated (C1024)."},
                ),
                objective_complete=True,
            ),
            AgentAction(decision=ReplanDecisionType.COMPLETE, reason="Workflow finished"),
        ]
    )

    async def fake_decide(state_manager):
        return next(scripted)

    monkeypatch.setattr(orchestrator, "decide_next_action", fake_decide)
    monkeypatch.setattr(orchestrator, "EventEmitter", lambda rid: _emitter(rid, events))

    await orchestrator.run_loop(run["id"], manager, run_repo, approval_repo)

    # No sheets.insert was ever called; the existing record was updated.
    tool_calls = [h.tool for h in manager.state.execution_history]
    assert "sheets.insert" not in tool_calls
    assert tool_calls == ["sheets.search", "sheets.update", "slack.send"]

    update_result = manager.state.execution_history[1].result
    assert update_result.success
    assert update_result.data["record"]["status"] == "reapplied"

    assert sent_messages[-1]["text"] == "Rahul Sharma re-applied; tracker updated (C1024)."

    event_types = [e["event_type"] for e in events.list_for_run(run["id"])]
    assert "REPLANNING" in event_types
    assert "WORKFLOW_COMPLETED" in event_types
    assert run_repo.get(run["id"])["status"] == RunStatus.COMPLETED.value
