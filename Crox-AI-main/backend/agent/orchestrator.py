from agent.events import EventEmitter
from agent.executor import Executor
from agent.replanner import decide_next_action
from agent.state import AgentStateManager
from models.schemas import EventType, ReplanDecisionType, RunStatus
from repositories.approval_repository import ApprovalRepository
from repositories.run_repository import RunRepository

MAX_ITERATIONS = 25

_CONTINUABLE = {
    ReplanDecisionType.CONTINUE,
    ReplanDecisionType.RETRY,
    ReplanDecisionType.ALTERNATIVE_ACTION,
}


class WorkflowPaused(Exception):
    """Raised internally to break out of the loop when the agent needs the
    user before it can safely continue."""


# run_id -> "paused" | "stopped". Checked at the top of every loop iteration
# so /agent/pause and /agent/stop take effect between tool calls rather than
# needing to interrupt an in-flight Gemini/tool call.
_control: dict[str, str] = {}


def pause(run_id: str) -> None:
    _control[run_id] = "paused"


def resume(run_id: str) -> None:
    _control.pop(run_id, None)


def stop(run_id: str) -> None:
    _control[run_id] = "stopped"


def status(run_id: str) -> str | None:
    return _control.get(run_id)


async def _ask_user(run_id, action, run_repo, approval_repo, emitter) -> None:
    approval = approval_repo.create(run_id, "user_input")
    run_repo.update_status(run_id, RunStatus.AWAITING_USER_INPUT.value)
    await emitter.emit(
        EventType.USER_INPUT_REQUIRED,
        output={
            "approval_id": approval["id"],
            "question": action.ask_user_question or action.reason,
            "options": action.ask_user_options,
        },
    )


async def run_loop(
    run_id: str,
    state_manager: AgentStateManager,
    run_repo: RunRepository | None = None,
    approval_repo: ApprovalRepository | None = None,
) -> None:
    """The core loop from the spec:

    decide next action -> execute -> observe result -> update state ->
    decide next action -> ... -> COMPLETE / FAIL / ASK_USER

    This never just walks the plan's step list -- every iteration re-asks
    Gemini what should happen next given the actual current state.
    """
    run_repo = run_repo or RunRepository()
    approval_repo = approval_repo or ApprovalRepository()
    emitter = EventEmitter(run_id)
    executor = Executor()

    run_repo.update_status(run_id, RunStatus.RUNNING.value, started=True)
    await emitter.emit(EventType.WORKFLOW_STARTED)

    resume(run_id)  # clear any stale pause/stop flag from a previous run of this id

    try:
        for _ in range(MAX_ITERATIONS):
            if status(run_id) == "stopped":
                run_repo.update_status(run_id, RunStatus.STOPPED.value, completed=True)
                await emitter.emit(EventType.WORKFLOW_FAILED, error="stopped by user")
                return
            if status(run_id) == "paused":
                run_repo.update_status(run_id, RunStatus.PAUSED.value)
                return

            action = await decide_next_action(state_manager)
            state_manager.set_current_objective(action.current_objective)

            if action.decision == ReplanDecisionType.COMPLETE:
                run_repo.update_status(run_id, RunStatus.COMPLETED.value, completed=True)
                await emitter.emit(EventType.WORKFLOW_COMPLETED, output={"reason": action.reason})
                return

            if action.decision == ReplanDecisionType.FAIL:
                run_repo.update_status(run_id, RunStatus.FAILED.value, completed=True)
                await emitter.emit(EventType.WORKFLOW_FAILED, error=action.reason)
                return

            if action.decision == ReplanDecisionType.ASK_USER:
                await _ask_user(run_id, action, run_repo, approval_repo, emitter)
                raise WorkflowPaused()

            if action.decision in _CONTINUABLE:
                if action.decision == ReplanDecisionType.ALTERNATIVE_ACTION:
                    await emitter.emit(EventType.REPLANNING, output={"reason": action.reason})

                if not action.next_action:
                    # The model sometimes explains, in `reason`, that it wants
                    # to ask the user something without actually setting
                    # decision=ASK_USER. Rather than failing a recoverable
                    # run over a model formatting slip, treat "no next_action"
                    # as an implicit ASK_USER -- the whole point of this loop
                    # is to prefer asking the user over failing outright.
                    await _ask_user(run_id, action, run_repo, approval_repo, emitter)
                    raise WorkflowPaused()

                await executor.execute(action.next_action, state_manager, emitter)

                if action.objective_complete and action.current_objective:
                    state_manager.mark_completed(action.current_objective)
                    await emitter.emit(EventType.STEP_COMPLETED, output={"objective": action.current_objective})

        run_repo.update_status(run_id, RunStatus.FAILED.value, completed=True)
        await emitter.emit(EventType.WORKFLOW_FAILED, error="max iterations reached without completion")
    except WorkflowPaused:
        return
