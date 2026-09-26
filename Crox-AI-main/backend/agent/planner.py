from agent.gemini_client import generate_structured
from agent.prompts import planner_prompt
from models.schemas import WorkflowPlan
from tools.registry import list_tool_specs


async def generate_plan(goal: str) -> WorkflowPlan:
    """Generates the initial high-level workflow plan for a goal.

    The planner never returns executable code -- only a WorkflowPlan of
    human-readable objectives, validated by Pydantic before it can be
    persisted or shown to the user for approval.
    """
    tool_specs = list_tool_specs()
    prompt = planner_prompt(goal, tool_specs)
    plan = await generate_structured(prompt, WorkflowPlan)
    if not plan.goal:
        plan.goal = goal
    return plan
