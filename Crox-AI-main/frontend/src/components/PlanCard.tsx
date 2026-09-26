import type { PlanDecision, WorkflowPlan } from "../types";
import { AgentBadge } from "./AgentBadge";

export function PlanSteps({
  steps,
  completedObjectives = [],
  currentObjective = null,
  live = false,
}: {
  steps: WorkflowPlan["steps"];
  completedObjectives?: string[];
  currentObjective?: string | null;
  live?: boolean;
}) {
  return (
    <ol className="flex flex-col gap-1">
      {steps.map((step) => {
        const status = completedObjectives.includes(step.id)
          ? "done"
          : live && step.id === currentObjective
            ? "active"
            : "pending";
        return (
          <li key={step.id} className="flex items-baseline gap-2 text-[0.82rem]">
            <span
              className={`relative top-[1px] h-[11px] w-[11px] flex-none rounded-[3px] border-[1.5px] ${
                status === "done"
                  ? "border-[var(--silver)] bg-[var(--silver)] shadow-[0_0_8px_rgba(215,220,227,0.6)]"
                  : status === "active"
                    ? "animate-pulse border-[var(--silver-bright)] shadow-[0_0_10px_rgba(215,220,227,0.7)]"
                    : "border-white/25"
              }`}
            />
            <span className={status === "pending" ? "text-slate-500" : "text-white"}>{step.objective}</span>
          </li>
        );
      })}
    </ol>
  );
}

// The interactive card shown inline in chat when a plan is awaiting (or
// carries) a decision. Monochrome, same as every other card in the app --
// identity is carried by the "Planner" badge label, not by a color wash.
export function PlanCard({
  plan,
  decision,
  completedObjectives = [],
  currentObjective = null,
  live = false,
  busy = false,
  onApprove,
  onReject,
}: {
  plan: WorkflowPlan;
  decision: PlanDecision;
  completedObjectives?: string[];
  currentObjective?: string | null;
  live?: boolean;
  busy?: boolean;
  onApprove?: () => void;
  onReject?: () => void;
}) {
  const done = completedObjectives.length;
  return (
    <div className="glow-card rounded-xl p-3.5">
      <div className="flex flex-wrap items-center gap-2">
        <AgentBadge kind="planner" />
        <span className="text-[0.86rem] font-semibold text-slate-100">{plan.goal}</span>
        {done > 0 && (
          <span className="ml-auto text-xs text-slate-500">
            {done}/{plan.steps.length}
          </span>
        )}
      </div>
      <div className="mt-2.5">
        <PlanSteps steps={plan.steps} completedObjectives={completedObjectives} currentObjective={currentObjective} live={live} />
      </div>

      {decision === "pending" && onApprove && onReject && (
        <div className="mt-3.5 flex gap-2">
          <button onClick={onApprove} disabled={busy} className="glow-btn rounded-full px-4 py-1.5 text-[0.82rem] font-semibold">
            Approve
          </button>
          <button
            onClick={onReject}
            disabled={busy}
            className="hairline rounded-full border px-4 py-1.5 text-[0.82rem] font-medium text-slate-200 transition-colors hover:bg-white/5 disabled:opacity-50"
          >
            Reject
          </button>
        </div>
      )}
      {decision === "rejected" && <p className="mt-2.5 text-xs text-slate-500">Plan rejected — nothing was executed.</p>}
    </div>
  );
}
