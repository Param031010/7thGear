from __future__ import annotations

from enum import Enum
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Workflow planning
# ---------------------------------------------------------------------------

class WorkflowStep(BaseModel):
    id: str = Field(description="Short snake_case identifier for this objective")
    objective: str = Field(description="Human-readable description of what this step should accomplish")


class WorkflowPlan(BaseModel):
    goal: str
    steps: list[WorkflowStep]


# ---------------------------------------------------------------------------
# Tool calling
# ---------------------------------------------------------------------------

class ToolCall(BaseModel):
    tool: str
    arguments: dict[str, Any] = Field(default_factory=dict)


class ToolResult(BaseModel):
    success: bool
    data: dict[str, Any] = Field(default_factory=dict)
    error: Optional[str] = None


# ---------------------------------------------------------------------------
# Next-action / replanning decisions
#
# The agent asks Gemini "what should happen next" after every tool result.
# CONTINUE means "proceed with the next objective in the plan as expected";
# the other decisions cover the replanning paths described in the spec.
# ---------------------------------------------------------------------------

class ReplanDecisionType(str, Enum):
    CONTINUE = "CONTINUE"
    RETRY = "RETRY"
    ALTERNATIVE_ACTION = "ALTERNATIVE_ACTION"
    ASK_USER = "ASK_USER"
    COMPLETE = "COMPLETE"
    FAIL = "FAIL"


class AgentAction(BaseModel):
    decision: ReplanDecisionType
    reason: str = Field(description="Concise, user-facing explanation of why this action was chosen")
    current_objective: Optional[str] = Field(
        default=None, description="id of the plan step this action is working toward"
    )
    next_action: Optional[ToolCall] = Field(
        default=None, description="Tool call to execute next, required for CONTINUE/RETRY/ALTERNATIVE_ACTION"
    )
    objective_complete: bool = Field(
        default=False,
        description="True if executing next_action will fully satisfy current_objective",
    )
    ask_user_question: Optional[str] = None
    ask_user_options: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Agent state
# ---------------------------------------------------------------------------

class LastResult(BaseModel):
    tool: Optional[str] = None
    success: Optional[bool] = None
    data: dict[str, Any] = Field(default_factory=dict)
    error: Optional[str] = None


class HistoryEntry(BaseModel):
    tool: Optional[str] = None
    arguments: dict[str, Any] = Field(default_factory=dict)
    result: Optional[ToolResult] = None
    reason: Optional[str] = None


class AgentState(BaseModel):
    goal: str
    plan: WorkflowPlan
    current_objective: Optional[str] = None
    completed_objectives: list[str] = Field(default_factory=list)
    facts: dict[str, Any] = Field(default_factory=dict)
    execution_history: list[HistoryEntry] = Field(default_factory=list)
    last_result: Optional[LastResult] = None


# ---------------------------------------------------------------------------
# Execution / websocket events
# ---------------------------------------------------------------------------

class EventType(str, Enum):
    PLAN_CREATED = "PLAN_CREATED"
    APPROVAL_REQUIRED = "APPROVAL_REQUIRED"
    USER_APPROVED = "USER_APPROVED"
    USER_REJECTED = "USER_REJECTED"
    WORKFLOW_STARTED = "WORKFLOW_STARTED"
    STEP_STARTED = "STEP_STARTED"
    TOOL_CALLED = "TOOL_CALLED"
    TOOL_RESULT = "TOOL_RESULT"
    STEP_COMPLETED = "STEP_COMPLETED"
    REPLANNING = "REPLANNING"
    USER_INPUT_REQUIRED = "USER_INPUT_REQUIRED"
    WORKFLOW_COMPLETED = "WORKFLOW_COMPLETED"
    WORKFLOW_FAILED = "WORKFLOW_FAILED"


class RunStatus(str, Enum):
    PENDING = "pending"
    AWAITING_APPROVAL = "awaiting_approval"
    RUNNING = "running"
    PAUSED = "paused"
    AWAITING_USER_INPUT = "awaiting_user_input"
    COMPLETED = "completed"
    FAILED = "failed"
    STOPPED = "stopped"
    REJECTED = "rejected"


# ---------------------------------------------------------------------------
# API request/response bodies
# ---------------------------------------------------------------------------

class PlanRequest(BaseModel):
    goal: str


class RunIdRequest(BaseModel):
    run_id: str


class ApproveRequest(BaseModel):
    run_id: str
    approved: bool


class UserResponseRequest(BaseModel):
    run_id: str
    approval_id: str
    response: dict[str, Any]
