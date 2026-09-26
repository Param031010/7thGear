import { useMemo, useState } from "react";
import type { ExecutionEvent } from "../types";
import { AgentBadge, agentForEvent } from "./AgentBadge";
import { ToolIcon, type IconKind } from "./ToolIcon";

// Plain-language label + icon per tool, so the activity log reads like
// "Searching Gmail" instead of "Calling gmail.search".
const TOOL_META: Record<string, { label: string; icon: IconKind }> = {
  "gmail.search": { label: "Searching Gmail", icon: "gmail" },
  "gmail.read": { label: "Reading email", icon: "gmail" },
  "gmail.download_attachment": { label: "Downloading attachment", icon: "gmail" },
  "document.extract_text": { label: "Reading attachment", icon: "document" },
  "document.extract_fields": { label: "Extracting details", icon: "document" },
  "sheets.search": { label: "Checking tracker", icon: "sheets" },
  "sheets.insert": { label: "Updating CRM", icon: "sheets" },
  "sheets.update": { label: "Updating tracker", icon: "sheets" },
  "slack.send": { label: "Notifying Slack", icon: "slack" },
  "browser.navigate": { label: "Opening page", icon: "browser" },
  "browser.click": { label: "Clicking", icon: "browser" },
  "browser.type": { label: "Typing", icon: "browser" },
  "browser.get_text": { label: "Reading page", icon: "browser" },
  "desktop.open_app": { label: "Opening app", icon: "desktop" },
  "desktop.get_window": { label: "Finding window", icon: "desktop" },
  "desktop.click": { label: "Clicking", icon: "desktop" },
  "desktop.type": { label: "Typing", icon: "desktop" },
  "desktop.hotkey": { label: "Sending hotkey", icon: "desktop" },
};

interface ToolItem {
  kind: "tool";
  tool: string;
  status: "pending" | "success" | "error";
  error?: string | null;
}

interface MilestoneItem {
  kind: "milestone";
  event: ExecutionEvent;
}

type DisplayItem = ToolItem | MilestoneItem;

// A TOOL_CALLED + its matching TOOL_RESULT collapse into one row -- the log
// shouldn't say "Calling X" and then "X succeeded" as two separate lines.
// STEP_COMPLETED is dropped entirely; the plan card already shows step
// progress, so it's redundant here.
function buildItems(events: ExecutionEvent[]): DisplayItem[] {
  const items: DisplayItem[] = [];
  for (const event of events) {
    if (event.event_type === "TOOL_CALLED") {
      items.push({ kind: "tool", tool: event.tool_name ?? "", status: "pending" });
    } else if (event.event_type === "TOOL_RESULT") {
      const pending = [...items].reverse().find((it): it is ToolItem => it.kind === "tool" && it.tool === event.tool_name && it.status === "pending");
      if (pending) {
        pending.status = event.status === "success" ? "success" : "error";
        pending.error = event.error;
      } else {
        items.push({ kind: "tool", tool: event.tool_name ?? "", status: event.status === "success" ? "success" : "error", error: event.error });
      }
    } else if (event.event_type === "STEP_COMPLETED") {
      continue;
    } else {
      items.push({ kind: "milestone", event });
    }
  }
  return items;
}

function milestoneText(event: ExecutionEvent): string {
  switch (event.event_type) {
    case "PLAN_CREATED":
      return "Made a plan";
    case "APPROVAL_REQUIRED":
      return "Waiting for your approval";
    case "USER_APPROVED":
      return "You approved the plan";
    case "USER_REJECTED":
      return "You rejected the plan";
    case "WORKFLOW_STARTED":
      return "Started";
    case "REPLANNING":
      return String(event.output?.reason ?? "Changing approach");
    case "USER_INPUT_REQUIRED":
      return String(event.output?.question ?? "Needs your input");
    case "WORKFLOW_COMPLETED":
      return String(event.output?.reason ?? "All done");
    case "WORKFLOW_FAILED":
      return event.error || "Something went wrong";
    default:
      return event.event_type.replace(/_/g, " ").toLowerCase();
  }
}

function StatusDot({ status, milestone }: { status: "pending" | "success" | "error"; milestone?: boolean }) {
  return (
    <span
      className={`relative z-10 flex-none rounded-full border ${milestone ? "h-2.5 w-2.5" : "h-1.5 w-1.5"} ${
        status === "pending"
          ? "animate-pulse border-[var(--silver-bright)] bg-[var(--silver-bright)] shadow-[0_0_10px_rgba(215,220,227,0.8)]"
          : status === "error"
            ? "border-white bg-white"
            : "border-[var(--hairline-strong)] bg-[var(--silver-dim)]"
      }`}
    />
  );
}

// The icon doubles as the status indicator for tool rows: a spinning ring
// while the call is in flight, plain (dimmed on failure) once it resolves --
// so "reading Gmail" visibly shows the Gmail logo spinning until it's done.
function ToolIconSlot({ icon, status }: { icon: IconKind; status: "pending" | "success" | "error" }) {
  return (
    <span className="relative flex h-[23px] w-[23px] flex-none items-center justify-center">
      {status === "pending" && (
        <span
          className="absolute inset-0 animate-spin rounded-full border-[1.5px]"
          style={{ borderColor: "rgba(215,220,227,0.22)", borderTopColor: "var(--silver-bright)" }}
          aria-hidden="true"
        />
      )}
      <span className={status === "error" ? "opacity-50 grayscale" : "opacity-100"}>
        <ToolIcon icon={icon} />
      </span>
    </span>
  );
}

function ToolRow({ item }: { item: ToolItem }) {
  const meta = TOOL_META[item.tool] ?? { label: item.tool || "Working", icon: "generic" as IconKind };
  return (
    <li className="flex items-center gap-2 py-1 pl-0.5 text-[0.83rem]">
      <ToolIconSlot icon={meta.icon} status={item.status} />
      <span className={item.status === "error" ? "text-slate-200" : item.status === "pending" ? "text-slate-100" : "text-slate-500"}>
        {meta.label}
        {item.status === "error" && <span className="text-slate-500"> — couldn't finish</span>}
      </span>
    </li>
  );
}

function MilestoneRow({ event, active }: { event: ExecutionEvent; active: boolean }) {
  const failed = event.event_type === "WORKFLOW_FAILED";
  return (
    <li className="flex items-center gap-2.5 py-1 pl-0.5 text-[0.83rem]">
      <StatusDot status={active ? "pending" : failed ? "error" : "success"} milestone />
      <AgentBadge kind={agentForEvent(event.event_type)} />
      <span className={active ? "text-slate-100" : failed ? "text-slate-200" : "text-slate-500"}>{milestoneText(event)}</span>
    </li>
  );
}

export function Timeline({
  events,
  live = false,
  defaultOpen = false,
  bare = false,
}: {
  events: ExecutionEvent[];
  live?: boolean;
  defaultOpen?: boolean;
  bare?: boolean;
}) {
  const [open, setOpen] = useState(defaultOpen);
  const items = useMemo(() => buildItems(events), [events]);
  if (items.length === 0) return null;

  const rows = (
    <ol className="mt-2 list-none">
      {items.map((item, i) => {
        const isLast = live && i === items.length - 1;
        return item.kind === "tool" ? <ToolRow key={i} item={item} /> : <MilestoneRow key={i} event={item.event} active={isLast} />;
      })}
    </ol>
  );

  if (bare) return rows;

  const calls = items.filter((it) => it.kind === "tool").length;
  const replans = events.filter((e) => e.event_type === "REPLANNING").length;

  return (
    <div className="mt-2 border-t border-dashed border-[var(--hairline)] pt-2">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="inline-flex items-center gap-2 text-[0.78rem] text-accent transition-colors hover:text-accent-soft"
      >
        {open ? "Hide" : "Show"} agent activity
        <span className="text-slate-500">
          {calls > 0 ? `${calls} step${calls === 1 ? "" : "s"}` : ""}
          {calls > 0 && replans > 0 ? " · " : ""}
          {replans > 0 ? `${replans} replan${replans === 1 ? "" : "s"}` : ""}
        </span>
      </button>
      {open && rows}
    </div>
  );
}
