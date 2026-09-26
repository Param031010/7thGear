import pytest

from agent import planner
from models.schemas import WorkflowPlan, WorkflowStep


async def test_generate_plan_returns_validated_plan(monkeypatch):
    canned = WorkflowPlan(
        goal="",
        steps=[
            WorkflowStep(id="find_applications", objective="Find new internship applications"),
            WorkflowStep(id="extract_candidate", objective="Extract candidate information"),
        ],
    )

    async def fake_generate_structured(prompt, response_model):
        assert response_model is WorkflowPlan
        return canned

    monkeypatch.setattr(planner, "generate_structured", fake_generate_structured)

    plan = await planner.generate_plan("Process today's internship applications")

    assert plan.goal == "Process today's internship applications"
    assert len(plan.steps) == 2
    assert plan.steps[0].id == "find_applications"


async def test_generate_plan_propagates_gemini_errors(monkeypatch):
    async def fake_generate_structured(prompt, response_model):
        raise ValueError("gemini did not return valid JSON")

    monkeypatch.setattr(planner, "generate_structured", fake_generate_structured)

    with pytest.raises(ValueError):
        await planner.generate_plan("some goal")
