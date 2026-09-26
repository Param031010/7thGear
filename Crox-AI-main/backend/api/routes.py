import asyncio
from datetime import datetime

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect

from api.websocket import manager

from agent import orchestrator
from agent.events import EventEmitter
from agent.planner import generate_plan
from agent.state import AgentStateManager
from models.schemas import (
    ApproveRequest,
    EventType,
    PlanRequest,
    RunIdRequest,
    RunStatus,
    UserResponseRequest,
)
from repositories.approval_repository import ApprovalRepository
from repositories.event_repository import EventRepository
from repositories.run_repository import RunRepository
from repositories.workflow_repository import WorkflowRepository

router = APIRouter()

workflow_repo = WorkflowRepository()
run_repo = RunRepository()
event_repo = EventRepository()
approval_repo = ApprovalRepository()


def _start_execution_task(run_id: str, state_manager: AgentStateManager) -> None:
    asyncio.create_task(orchestrator.run_loop(run_id, state_manager, run_repo, approval_repo))


@router.post("/agent/plan")
async def create_plan(body: PlanRequest):
    plan = await generate_plan(body.goal)
    workflow = workflow_repo.create(name=body.goal[:80], goal=body.goal, plan=plan.model_dump())
    run = run_repo.create(workflow_id=workflow["id"], goal=body.goal)

    state_manager = AgentStateManager.new(run["id"], body.goal, plan)
    run_repo.update_status(run["id"], RunStatus.AWAITING_APPROVAL.value)

    emitter = EventEmitter(run["id"])
    await emitter.emit(EventType.PLAN_CREATED, output=plan.model_dump())
    approval = approval_repo.create(run["id"], "workflow_plan")
    await emitter.emit(EventType.APPROVAL_REQUIRED, output={"approval_id": approval["id"], "plan": plan.model_dump()})

    return {"workflow": workflow, "run": run, "plan": plan.model_dump(), "approval_id": approval["id"]}


@router.post("/agent/approve")
async def approve(body: ApproveRequest):
    run = run_repo.get(body.run_id)
    if not run:
        raise HTTPException(404, "run not found")

    approval = approval_repo.latest_pending_for_run(body.run_id, "workflow_plan")
    if approval:
        approval_repo.resolve(approval["id"], "approved" if body.approved else "rejected")

    emitter = EventEmitter(body.run_id)
    if not body.approved:
        run_repo.update_status(body.run_id, RunStatus.REJECTED.value, completed=True)
        await emitter.emit(EventType.USER_REJECTED)
        return {"status": "rejected"}

    await emitter.emit(EventType.USER_APPROVED)
    state_manager = AgentStateManager.load(body.run_id)
    if not state_manager:
        raise HTTPException(500, "agent state not found for run")

    _start_execution_task(body.run_id, state_manager)
    return {"status": "started"}


@router.post("/agent/run")
async def run_now(body: RunIdRequest):
    """Manually (re)start execution for a run that is approved but idle,
    e.g. after a backend restart. Loads state fresh from Supabase."""
    state_manager = AgentStateManager.load(body.run_id)
    if not state_manager:
        raise HTTPException(404, "agent state not found for run")
    _start_execution_task(body.run_id, state_manager)
    return {"status": "started"}


@router.post("/agent/pause")
async def pause(body: RunIdRequest):
    orchestrator.pause(body.run_id)
    return {"status": "pausing"}


@router.post("/agent/resume")
async def resume(body: RunIdRequest):
    state_manager = AgentStateManager.load(body.run_id)
    if not state_manager:
        raise HTTPException(404, "agent state not found for run")
    orchestrator.resume(body.run_id)
    run_repo.update_status(body.run_id, RunStatus.RUNNING.value)
    _start_execution_task(body.run_id, state_manager)
    return {"status": "resumed"}


@router.post("/agent/stop")
async def stop_run(body: RunIdRequest):
    orchestrator.stop(body.run_id)
    return {"status": "stopping"}


@router.post("/user-response")
async def user_response(body: UserResponseRequest):
    approval = approval_repo.get(body.approval_id)
    if not approval or approval["run_id"] != body.run_id:
        raise HTTPException(404, "approval not found for run")

    approval_repo.resolve(body.approval_id, "answered", body.response)

    state_manager = AgentStateManager.load(body.run_id)
    if not state_manager:
        raise HTTPException(404, "agent state not found for run")
    state_manager.update_facts({"user_response": body.response})

    orchestrator.resume(body.run_id)
    run_repo.update_status(body.run_id, RunStatus.RUNNING.value)
    _start_execution_task(body.run_id, state_manager)
    return {"status": "resumed"}


@router.get("/workflows")
async def list_workflows():
    return workflow_repo.list()


@router.get("/workflows/{workflow_id}")
async def get_workflow(workflow_id: str):
    workflow = workflow_repo.get(workflow_id)
    if not workflow:
        raise HTTPException(404, "workflow not found")
    return {"workflow": workflow, "steps": workflow_repo.get_steps(workflow_id)}


@router.get("/runs")
async def list_runs():
    return run_repo.list()


@router.get("/runs/{run_id}")
async def get_run(run_id: str):
    run = run_repo.get(run_id)
    if not run:
        raise HTTPException(404, "run not found")
    state_manager = AgentStateManager.load(run_id)
    return {
        "run": run,
        "state": state_manager.to_public_dict() if state_manager else None,
        "events": event_repo.list_for_run(run_id),
    }


@router.delete("/runs/{run_id}")
async def delete_run(run_id: str):
    run = run_repo.get(run_id)
    if not run:
        raise HTTPException(404, "run not found")
    orchestrator.stop(run_id)  # halt any in-progress loop before its rows disappear under it
    run_repo.delete(run_id)  # cascades to execution_events, agent_state, approvals
    if run.get("workflow_id"):
        try:
            workflow_repo.delete(run["workflow_id"])
        except Exception:
            pass  # best-effort cleanup of the 1:1 workflow row; the run is already gone
    return {"status": "deleted"}


@router.get("/dashboard/summary")
async def dashboard_summary():
    """All figures are derived from Supabase rows, never hardcoded."""
    workflows = workflow_repo.list()
    runs = run_repo.list()

    active_workflows = sum(1 for w in workflows if w["status"] not in ("rejected", "failed"))
    successful_runs = sum(1 for r in runs if r["status"] == "completed")

    execution_seconds = 0.0
    for r in runs:
        if r.get("started_at") and r.get("completed_at"):
            started = datetime.fromisoformat(r["started_at"].replace("Z", "+00:00"))
            completed = datetime.fromisoformat(r["completed_at"].replace("Z", "+00:00"))
            execution_seconds += max((completed - started).total_seconds(), 0)

    recent = sorted(runs, key=lambda r: r["created_at"], reverse=True)[:5]

    return {
        "active_workflows": active_workflows,
        "total_runs": len(runs),
        "successful_runs": successful_runs,
        "agent_execution_seconds": execution_seconds,
        "recent_runs": recent,
    }


@router.websocket("/ws/runs/{run_id}")
async def run_events_ws(websocket: WebSocket, run_id: str):
    await manager.connect(run_id, websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(run_id, websocket)
