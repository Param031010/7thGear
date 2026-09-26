export type AgentKind = "planner" | "executor" | "replanner" | "user" | "system";

const LABELS: Record<AgentKind, string> = {
  planner: "Planner",
  executor: "Executor",
  replanner: "Replanner",
  user: "You",
  system: "System",
};

// One consistent monochrome style for every agent -- identity is carried by
// the label text, not by color.
export function AgentBadge({ kind, label }: { kind: AgentKind; label?: string }) {
  return (
    <span className="inline-flex flex-none items-center rounded-full border border-[var(--hairline-strong)] px-1.5 py-0.5 text-[0.62rem] font-semibold uppercase tracking-wide text-[var(--silver-bright)] shadow-[0_0_10px_-3px_rgba(215,220,227,0.45)]">
      {label ?? LABELS[kind]}
    </span>
  );
}

// Maps a backend EventType to which "agent" conceptually produced it, so the
// chat timeline reads as a hand-off between planner/executor/replanner
// (mirroring the orchestrator's actual decide -> execute -> replan loop)
// rather than a flat list of opaque event names.
export function agentForEvent(eventType: string): AgentKind {
  switch (eventType) {
    case "PLAN_CREATED":
    case "APPROVAL_REQUIRED":
      return "planner";
    case "TOOL_CALLED":
    case "TOOL_RESULT":
    case "STEP_COMPLETED":
      return "executor";
    case "REPLANNING":
      return "replanner";
    case "USER_INPUT_REQUIRED":
    case "USER_APPROVED":
    case "USER_REJECTED":
      return "user";
    default:
      return "system";
  }
}
