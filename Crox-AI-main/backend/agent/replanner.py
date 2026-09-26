from agent.gemini_client import generate_structured
from agent.prompts import next_action_prompt
from agent.state import AgentStateManager
from models.schemas import AgentAction
from tools.registry import list_tool_specs


async def decide_next_action(state_manager: AgentStateManager) -> AgentAction:
    """The core "what should the agent do next" call. Invoked after every
    tool result (including the very first, with latest_result=None), so the
    plan is never blindly followed step-by-step -- every action is chosen
    against the actual current state.
    """
    state = state_manager.state
    tool_specs = list_tool_specs()

    latest_result = None
    if state.last_result is not None:
        latest_result = state.last_result.model_dump()

    prompt = next_action_prompt(
        goal=state.goal,
        plan=state.plan.model_dump(),
        state=state_manager.to_public_dict(),
        latest_result=latest_result,
        tool_specs=tool_specs,
    )
    return await generate_structured(prompt, AgentAction)
