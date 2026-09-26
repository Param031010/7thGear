import type {
  AgentStateSnapshot,
  DashboardSummary,
  ExecutionEvent,
  PlanResponse,
  Workflow,
  WorkflowRun,
} from "../types";

const BASE_URL = window.workflowos?.backendUrl || "http://127.0.0.1:8000";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`${options?.method || "GET"} ${path} failed (${res.status}): ${body}`);
  }
  return res.json() as Promise<T>;
}

export const api = {
  baseUrl: BASE_URL,

  createPlan: (goal: string) =>
    request<PlanResponse>("/agent/plan", { method: "POST", body: JSON.stringify({ goal }) }),

  approve: (runId: string, approved: boolean) =>
    request<{ status: string }>("/agent/approve", {
      method: "POST",
      body: JSON.stringify({ run_id: runId, approved }),
    }),

  pause: (runId: string) =>
    request<{ status: string }>("/agent/pause", { method: "POST", body: JSON.stringify({ run_id: runId }) }),

  resume: (runId: string) =>
    request<{ status: string }>("/agent/resume", { method: "POST", body: JSON.stringify({ run_id: runId }) }),

  stop: (runId: string) =>
    request<{ status: string }>("/agent/stop", { method: "POST", body: JSON.stringify({ run_id: runId }) }),

  respondToUser: (runId: string, approvalId: string, response: Record<string, unknown>) =>
    request<{ status: string }>("/user-response", {
      method: "POST",
      body: JSON.stringify({ run_id: runId, approval_id: approvalId, response }),
    }),

  listWorkflows: () => request<Workflow[]>("/workflows"),

  getWorkflow: (id: string) => request<{ workflow: Workflow; steps: unknown[] }>(`/workflows/${id}`),

  listRuns: () => request<WorkflowRun[]>("/runs"),

  getRun: (id: string) =>
    request<{ run: WorkflowRun; state: AgentStateSnapshot | null; events: ExecutionEvent[] }>(`/runs/${id}`),

  deleteRun: (id: string) => request<{ status: string }>(`/runs/${id}`, { method: "DELETE" }),

  dashboardSummary: () => request<DashboardSummary>("/dashboard/summary"),
};

export function wsUrl(runId: string): string {
  return `${BASE_URL.replace(/^http/, "ws")}/ws/runs/${runId}`;
}
