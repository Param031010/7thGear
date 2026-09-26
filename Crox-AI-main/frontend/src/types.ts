export interface WorkflowStep {
  id: string;
  objective: string;
}

export interface WorkflowPlan {
  goal: string;
  steps: WorkflowStep[];
}

export interface Workflow {
  id: string;
  name: string;
  description: string | null;
  goal: string;
  plan: WorkflowPlan;
  status: string;
  created_at: string;
  updated_at: string;
}

export interface WorkflowRun {
  id: string;
  workflow_id: string | null;
  goal: string;
  status: string;
  current_step: string | null;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
}

export interface ExecutionEvent {
  id?: string;
  run_id?: string;
  event_type: string;
  tool_name: string | null;
  input: Record<string, unknown> | null;
  output: Record<string, unknown> | null;
  status: string | null;
  error: string | null;
  created_at: string;
}

export interface AgentStateSnapshot {
  goal: string;
  plan: WorkflowPlan;
  current_objective: string | null;
  completed_objectives: string[];
  facts: Record<string, unknown>;
  execution_history: Array<{
    tool: string | null;
    arguments: Record<string, unknown>;
    result: { success: boolean; data: Record<string, unknown>; error: string | null } | null;
    reason: string | null;
  }>;
  last_result: { tool: string | null; success: boolean | null; data: Record<string, unknown>; error: string | null } | null;
}

export interface DashboardSummary {
  active_workflows: number;
  total_runs: number;
  successful_runs: number;
  agent_execution_seconds: number;
  recent_runs: WorkflowRun[];
}

export interface PlanResponse {
  workflow: Workflow;
  run: WorkflowRun;
  plan: WorkflowPlan;
  approval_id: string;
}

export type PlanDecision = "pending" | "approved" | "rejected";

// One exchange in the chat: a user goal, and the assistant message that
// carries the plan, the live (or replayed) activity timeline, and the
// eventual outcome. A "chat" in this UI is one workflow run.
export interface ChatMessage {
  role: "user" | "assistant";
  runId?: string;
  goal?: string;
  plan?: WorkflowPlan;
  approvalId?: string | null;
  decision?: PlanDecision;
  events: ExecutionEvent[];
  status?: string;
  finalText?: string;
  askUser?: {
    approvalId: string;
    question: string;
    options: string[];
    answered: boolean;
  } | null;
}

