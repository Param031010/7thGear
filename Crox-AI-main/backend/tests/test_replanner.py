from agent import replanner
from agent.state import AgentStateManager
from models.schemas import AgentAction, ReplanDecisionType, ToolCall, WorkflowPlan, WorkflowStep
from tests.fakes import FakeStateRepository


def _manager():
    plan = WorkflowPlan(goal="g", steps=[WorkflowStep(id="find", objective="find candidate")])
    return AgentStateManager.new("run-replan", "g", plan, repository=FakeStateRepository())


async def test_decide_next_action_returns_validated_action(monkeypatch):
    canned = AgentAction(
        decision=ReplanDecisionType.CONTINUE,
        reason="starting the plan",
        current_objective="find",
        next_action=ToolCall(tool="gmail.search", arguments={}),
    )

    async def fake_generate_structured(prompt, response_model):
        assert response_model is AgentAction
        assert "find candidate" in prompt  # plan objective made it into the prompt
        return canned

    monkeypatch.setattr(replanner, "generate_structured", fake_generate_structured)

    action = await replanner.decide_next_action(_manager())

    assert action.decision == ReplanDecisionType.CONTINUE
    assert action.next_action.tool == "gmail.search"


async def test_decide_next_action_includes_latest_result_in_prompt(monkeypatch):
    manager = _manager()
    from models.schemas import ToolResult

    manager.record_tool_call("sheets.search", {"email": "x"}, ToolResult(success=True, data={"found": True}))

    seen_prompt = {}

    async def fake_generate_structured(prompt, response_model):
        seen_prompt["value"] = prompt
        return AgentAction(decision=ReplanDecisionType.ALTERNATIVE_ACTION, reason="candidate exists")

    monkeypatch.setattr(replanner, "generate_structured", fake_generate_structured)

    await replanner.decide_next_action(manager)

    assert '"found": true' in seen_prompt["value"]
