import { useEffect, useRef, useState, type HTMLAttributes, type PointerEvent as ReactPointerEvent, type ReactNode } from "react";
import type { AgentStateSnapshot, DashboardSummary, ExecutionEvent, WorkflowRun } from "../types";
import { api } from "../services/api";
import { StatusBadge } from "./StatusBadge";
import { PlanSteps } from "./PlanCard";
import { Timeline } from "./Timeline";
import {
  SLOTS,
  WIDGET_INFO,
  dockWidget,
  effectiveLayout,
  floatWidget,
  sendHome,
  useMediaQuery,
  type SlotId,
  type WidgetId,
  type WidgetLayout,
} from "../widgetLayout";

type Handle = HTMLAttributes<HTMLElement>;

function formatDuration(seconds: number): string {
  if (seconds < 60) return `${Math.round(seconds)}s`;
  const minutes = Math.floor(seconds / 60);
  const hours = Math.floor(minutes / 60);
  if (hours > 0) return `${hours}h ${minutes % 60}m`;
  return `${minutes}m ${Math.round(seconds % 60)}s`;
}

const SIDE_EFFECT_TOOLS = new Set(["sheets.insert", "sheets.update", "slack.send", "gmail.download_attachment"]);

function describeAction(
  tool: string,
  args: Record<string, unknown>,
  data: Record<string, unknown>,
): { label: string; detail: string; url?: string } {
  switch (tool) {
    case "sheets.insert":
      return { label: "Added candidate", detail: String(args.name ?? args.email ?? ""), url: (data.resume_url as string) || undefined };
    case "sheets.update":
      return { label: "Updated candidate", detail: String(args.record_id ?? "") };
    case "slack.send":
      return { label: "Notified Slack", detail: `${args.channel ?? ""}: ${String(args.text ?? "").slice(0, 80)}` };
    case "gmail.download_attachment":
      return {
        label: "Downloaded resume",
        detail: String(data.storage_url ?? args.message_id ?? ""),
        url: (data.storage_url as string) || undefined,
      };
    default:
      return { label: tool, detail: "" };
  }
}

function Skeleton() {
  return (
    <div className="flex flex-col gap-2 pt-1" aria-label="Loading">
      <span className="h-2.5 w-full animate-pulse rounded-md bg-white/5" />
      <span className="h-2.5 w-4/5 animate-pulse rounded-md bg-white/5" />
      <span className="h-2.5 w-3/5 animate-pulse rounded-md bg-white/5" />
    </div>
  );
}

// The card every widget shares -- git_show's .widget: translucent dark face,
// hairline border, rounded corners. The header is the drag handle.
function Widget({ title, meta, handle, children }: { title: string; meta?: string; handle?: Handle; children: ReactNode }) {
  return (
    <section className="glow-card flex h-full min-h-0 flex-col gap-2.5 rounded-[14px] px-[0.95rem] py-[0.85rem] backdrop-blur-md">
      <header
        {...handle}
        className={`flex flex-none items-baseline justify-between gap-2 ${handle?.onPointerDown ? "cursor-grab touch-none select-none active:cursor-grabbing" : ""}`}
      >
        <h3 className="glow-title text-[0.72rem] font-semibold uppercase tracking-[0.1em]">{title}</h3>
        {meta && <span className="truncate text-xs text-slate-500">{meta}</span>}
      </header>
      <div className="min-h-0 flex-1 overflow-y-auto pr-0.5">{children}</div>
    </section>
  );
}

// --- the six widgets ----------------------------------------------------------

function StatsWidget({ summary, handle }: { summary: DashboardSummary | null; handle?: Handle }) {
  return (
    <Widget title="Stats" handle={handle}>
      {!summary ? (
        <Skeleton />
      ) : (
        <div className="grid grid-cols-3 gap-2 pt-1 text-center">
          <div>
            <div className="text-lg font-semibold text-slate-100">{summary.active_workflows}</div>
            <div className="text-[0.65rem] text-slate-500">Active</div>
          </div>
          <div>
            <div className="text-lg font-semibold text-slate-100">
              {summary.successful_runs}/{summary.total_runs}
            </div>
            <div className="text-[0.65rem] text-slate-500">Successful</div>
          </div>
          <div>
            <div className="text-lg font-semibold text-slate-100">{formatDuration(summary.agent_execution_seconds)}</div>
            <div className="text-[0.65rem] text-slate-500">Exec time</div>
          </div>
        </div>
      )}
    </Widget>
  );
}

function RunsWidget({ summary, onOpenRun, handle }: { summary: DashboardSummary | null; onOpenRun: (id: string) => void; handle?: Handle }) {
  return (
    <Widget title="Recent runs" meta={summary ? `${summary.total_runs}` : undefined} handle={handle}>
      {!summary ? (
        <Skeleton />
      ) : summary.recent_runs.length === 0 ? (
        <p className="text-[0.8rem] text-slate-500">Nothing yet — send a goal to start.</p>
      ) : (
        <ul className="space-y-0.5">
          {summary.recent_runs.map((r) => (
            <li key={r.id}>
              <button
                onClick={() => onOpenRun(r.id)}
                className="flex w-full items-center justify-between gap-2 rounded-lg px-1.5 py-1 text-left text-[0.8rem] text-slate-300 transition-colors hover:bg-white/5"
              >
                <span className="truncate">{r.goal}</span>
                <StatusBadge status={r.status} />
              </button>
            </li>
          ))}
        </ul>
      )}
    </Widget>
  );
}

function ActionsWidget({ state, handle }: { state: AgentStateSnapshot | null; handle?: Handle }) {
  const actions = (state?.execution_history ?? []).filter((h) => h.tool && SIDE_EFFECT_TOOLS.has(h.tool) && h.result?.success);
  return (
    <Widget title="Actions taken" meta={actions.length ? `${actions.length}` : undefined} handle={handle}>
      {actions.length === 0 ? (
        <p className="text-[0.8rem] text-slate-500">Nothing changed yet. Changes the agent makes will be listed here.</p>
      ) : (
        <ol className="space-y-1">
          {actions.map((h, i) => {
            const { label, detail, url } = describeAction(h.tool!, h.arguments, h.result?.data ?? {});
            const body = (
              <>
                <span className="block text-[0.8rem] text-slate-100">{label}</span>
                <span className="block truncate text-[0.7rem] text-slate-500">{detail}</span>
              </>
            );
            return (
              <li key={i} className="rounded-lg px-1.5 py-1 hover:bg-white/5">
                {url ? (
                  <a href={url} target="_blank" rel="noreferrer">
                    {body}
                  </a>
                ) : (
                  body
                )}
              </li>
            );
          })}
        </ol>
      )}
    </Widget>
  );
}

function PlanWidget({ state, live, handle }: { state: AgentStateSnapshot | null; live: boolean; handle?: Handle }) {
  const steps = state?.plan?.steps ?? [];
  return (
    <Widget
      title="Current plan"
      meta={steps.length ? `${live ? "Working · " : ""}${state!.completed_objectives.length}/${steps.length}` : undefined}
      handle={handle}
    >
      {steps.length === 0 ? (
        <p className="text-[0.8rem] text-slate-500">No plan yet. One appears here when you send a goal.</p>
      ) : (
        <div className="space-y-2">
          <p className="text-[0.84rem] text-white">{state!.plan.goal}</p>
          <PlanSteps steps={steps} completedObjectives={state!.completed_objectives} currentObjective={state!.current_objective} live={live} />
        </div>
      )}
    </Widget>
  );
}

function TimelineWidget({ events, live, handle }: { events: ExecutionEvent[]; live: boolean; handle?: Handle }) {
  return (
    <Widget title="Execution timeline" meta={events.length ? `${events.length}` : undefined} handle={handle}>
      {events.length === 0 ? (
        <p className="text-[0.8rem] text-slate-500">Nothing running yet.</p>
      ) : (
        <Timeline events={events} live={live} defaultOpen bare />
      )}
    </Widget>
  );
}

function humanizeKey(key: string): string {
  const words = key.replace(/_/g, " ").trim().split(/\s+/);
  return words.map((w) => (w.length <= 3 ? w.toUpperCase() : w[0].toUpperCase() + w.slice(1))).join(" ");
}

function FactValue({ value }: { value: unknown }) {
  if (Array.isArray(value)) {
    if (value.length === 0) return <span className="text-slate-600">none</span>;
    return <span>{value.map(String).join(", ")}</span>;
  }
  if (value && typeof value === "object") {
    return <span className="font-mono text-[0.72rem] text-slate-400">{JSON.stringify(value)}</span>;
  }
  const text = String(value ?? "");
  if (/^https?:\/\//.test(text)) {
    let short = text;
    try {
      const u = new URL(text);
      short = u.hostname.replace(/^www\./, "") + (u.pathname.length > 1 ? "/…" : "");
    } catch {
      /* keep full text */
    }
    return (
      <a href={text} target="_blank" rel="noreferrer" className="text-accent underline decoration-accent/30 underline-offset-2 hover:text-accent-soft">
        {short}
      </a>
    );
  }
  return <span>{text || "—"}</span>;
}

function StateWidget({ state, handle }: { state: AgentStateSnapshot | null; handle?: Handle }) {
  if (!state) {
    return (
      <Widget title="Agent state" handle={handle}>
        <p className="text-[0.8rem] text-slate-500">No active run.</p>
      </Widget>
    );
  }

  const currentStep = state.plan?.steps?.find((s) => s.id === state.current_objective);
  const objectiveLabel = currentStep?.objective ?? (state.current_objective ? humanizeKey(state.current_objective) : null);
  const facts = Object.entries(state.facts ?? {});

  return (
    <Widget title="Agent state" handle={handle}>
      <div className="space-y-3.5">
        <div>
          <div className="text-[0.68rem] uppercase tracking-wide text-slate-500">Working on</div>
          <div className="mt-0.5 text-[0.85rem] text-white">{objectiveLabel ?? "—"}</div>
        </div>

        <div>
          <div className="text-[0.68rem] uppercase tracking-wide text-slate-500">What it knows so far</div>
          {facts.length === 0 ? (
            <p className="mt-1.5 text-[0.8rem] text-slate-600">Nothing gathered yet.</p>
          ) : (
            <dl className="mt-1.5 divide-y divide-white/5">
              {facts.map(([key, value]) => (
                <div key={key} className="flex items-start justify-between gap-3 py-1.5 text-[0.8rem]">
                  <dt className="flex-none text-slate-500">{humanizeKey(key)}</dt>
                  <dd className="min-w-0 truncate text-right text-slate-200">
                    <FactValue value={value} />
                  </dd>
                </div>
              ))}
            </dl>
          )}
        </div>
      </div>
    </Widget>
  );
}

// --- the floating panel -------------------------------------------------------

// Relative heights of the home slots in each column.
const SLOT_FLEX: Record<SlotId, number> = { L1: 0.7, L2: 1.15, L3: 1, R1: 1.15, R2: 1.15, R3: 0.9 };
// A dragged widget snaps to a slot when the pointer is over it, or when at
// least this share of it (or of the slot, if smaller) overlaps the slot.
const SNAP_OVERLAP = 0.5;
// How long a widget glides into (or out of) a slot.
const SNAP_GLIDE_MS = 140;
// Movement below this is a click (or half a double-click), not a drag.
const DRAG_THRESHOLD = 4;
// A floating widget always keeps this much of itself inside the chat area.
const KEEP_VISIBLE = 56;

const clamp = (value: number, lo: number, hi: number) => Math.min(Math.max(value, lo), Math.max(lo, hi));

interface Rect {
  x: number;
  y: number;
  w: number;
  h: number;
}

export interface FloatingWidgetsProps {
  run: WorkflowRun | null;
  state: AgentStateSnapshot | null;
  events: ExecutionEvent[];
  live: boolean;
  refreshKey: number;
  onOpenRun: (id: string) => void;
  layout: WidgetLayout;
  setLayout: (update: (l: WidgetLayout) => WidgetLayout) => void;
  drawerOpen: boolean;
  onCloseDrawer: () => void;
}

// Six cards floating over the chat area, three per side. On wide screens
// each sits in a home slot and can be dragged by its header anywhere in the
// chat area: near a slot it snaps in (swapping with whatever was there),
// anywhere else it floats where it's dropped. Double-clicking a header sends
// it home. On narrower screens they stack in one drawer and don't move.
export function FloatingWidgets({
  state,
  events,
  live,
  refreshKey,
  onOpenRun,
  layout,
  setLayout,
  drawerOpen,
  onCloseDrawer,
}: FloatingWidgetsProps) {
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  useEffect(() => {
    api.dashboardSummary().then(setSummary).catch(() => undefined);
  }, [refreshKey]);

  const wide = useMediaQuery("(min-width: 1200px)");
  const rootRef = useRef<HTMLDivElement>(null);
  const [drag, setDrag] = useState<(Rect & { id: WidgetId }) | null>(null);
  const [area, setArea] = useState<{ w: number; h: number } | null>(null);
  const placed = effectiveLayout(layout);

  // Floating widgets are kept inside the chat area as the window resizes.
  useEffect(() => {
    const hero = rootRef.current?.closest<HTMLElement>("[data-hero]");
    if (!hero) return;
    const observer = new ResizeObserver(() => setArea({ w: hero.clientWidth, h: hero.clientHeight }));
    observer.observe(hero);
    return () => observer.disconnect();
  }, [wide]);

  const render: Record<WidgetId, (handle?: Handle) => ReactNode> = {
    stats: (h) => <StatsWidget summary={summary} handle={h} />,
    runs: (h) => <RunsWidget summary={summary} onOpenRun={onOpenRun} handle={h} />,
    actions: (h) => <ActionsWidget state={state} handle={h} />,
    plan: (h) => <PlanWidget state={state} live={live} handle={h} />,
    timeline: (h) => <TimelineWidget events={events} live={live} handle={h} />,
    state: (h) => <StateWidget state={state} handle={h} />,
  };

  // React renders the dragged copy once when a drag starts; after that it's
  // moved directly (a transform per animation frame), so dragging stays
  // smooth however much is on screen.
  const startDrag = (id: WidgetId, e: ReactPointerEvent<HTMLElement>) => {
    if (e.button !== 0) return;
    e.preventDefault();
    const target = e.currentTarget;
    const hero = target.closest<HTMLElement>("[data-hero]");
    const card = target.closest<HTMLElement>("section");
    if (!hero || !card) return;
    const areaRect = hero.getBoundingClientRect();
    const box = card.getBoundingClientRect();
    const grab = { x: e.clientX - box.left, y: e.clientY - box.top };
    const startAt = { x: e.clientX, y: e.clientY };
    const slots = [...hero.querySelectorAll<HTMLElement>("[data-slot]")].map((el) => {
      const r = el.getBoundingClientRect();
      return { slot: el.dataset.slot as SlotId, x: r.left - areaRect.left, y: r.top - areaRect.top, w: r.width, h: r.height };
    });
    const overlap = (x: number, y: number, r: Rect) => {
      const ow = Math.min(x + box.width, r.x + r.w) - Math.max(x, r.x);
      const oh = Math.min(y + box.height, r.y + r.h) - Math.max(y, r.y);
      return ow > 0 && oh > 0 ? (ow * oh) / Math.min(box.width * box.height, r.w * r.h) : 0;
    };
    // The slot it's lifted from only joins the magnet once the widget has
    // left it, or the widget would stick there at the start of every drag.
    const originSlot = target.closest<HTMLElement>("[data-slot]")?.dataset.slot;
    const origin = slots.find((r) => r.slot === originSlot);
    let armed = !origin;
    let started = false;
    let last: (Rect & { snap: (Rect & { slot: SlotId }) | null }) | null = null;
    let frame = 0;
    let snappedTo: SlotId | null = null;
    let glideTimer = 0;

    const paint = () => {
      frame = 0;
      const el = hero.querySelector<HTMLElement>(".widget-dragging");
      if (!el || !last) return;
      const slot = last.snap?.slot ?? null;
      if (slot !== snappedTo) {
        // Glide into a slot, and back out to the pointer when leaving it.
        window.clearTimeout(glideTimer);
        el.classList.add("widget-dragging-snapped");
        if (!slot) glideTimer = window.setTimeout(() => el.classList.remove("widget-dragging-snapped"), SNAP_GLIDE_MS);
        snappedTo = slot;
      }
      const r = last.snap ?? last;
      el.style.transform = `translate3d(${r.x}px, ${r.y}px, 0)`;
      el.style.width = `${r.w}px`;
      el.style.height = `${r.h}px`;
    };

    const onMove = (ev: PointerEvent) => {
      if (!started) {
        if (Math.hypot(ev.clientX - startAt.x, ev.clientY - startAt.y) < DRAG_THRESHOLD) return;
        started = true;
        setDrag({ id, x: box.left - areaRect.left, y: box.top - areaRect.top, w: box.width, h: box.height });
      }
      const px = ev.clientX - areaRect.left;
      const py = ev.clientY - areaRect.top;
      const x = clamp(px - grab.x, KEEP_VISIBLE - box.width, areaRect.width - KEEP_VISIBLE);
      const y = clamp(py - grab.y, 0, areaRect.height - KEEP_VISIBLE);
      if (!armed && origin && overlap(x, y, origin) < SNAP_OVERLAP) armed = true;
      const targets = armed ? slots : slots.filter((r) => r !== origin);
      let snap = targets.find((r) => px >= r.x && px <= r.x + r.w && py >= r.y && py <= r.y + r.h) ?? null;
      if (!snap) {
        let best = SNAP_OVERLAP;
        for (const r of targets) {
          const share = overlap(x, y, r);
          if (share >= best) {
            best = share;
            snap = r;
          }
        }
      }
      last = { x, y, w: box.width, h: box.height, snap };
      if (!frame) frame = requestAnimationFrame(paint);
    };

    const onUp = () => {
      window.removeEventListener("pointermove", onMove);
      window.removeEventListener("pointerup", onUp);
      window.removeEventListener("pointercancel", onUp);
      cancelAnimationFrame(frame);
      window.clearTimeout(glideTimer);
      if (started && last) {
        const done = last;
        setLayout((l) =>
          done.snap
            ? dockWidget(effectiveLayout(l), id, done.snap.slot)
            : floatWidget(effectiveLayout(l), id, { x: done.x, y: done.y, w: done.w, h: done.h }),
        );
      }
      setDrag(null);
    };

    window.addEventListener("pointermove", onMove);
    window.addEventListener("pointerup", onUp);
    window.addEventListener("pointercancel", onUp);
  };

  const handleFor = (id: WidgetId): Handle => ({
    onPointerDown: (e) => startDrag(id, e as ReactPointerEvent<HTMLElement>),
    onDoubleClick: () => setLayout((l) => sendHome(effectiveLayout(l), id)),
    title: "Drag to move · double-click to send back",
  });

  if (!wide) {
    return (
      <div ref={rootRef}>
        <div
          className={`fixed inset-0 z-30 bg-black/50 transition-opacity ${drawerOpen ? "opacity-100" : "pointer-events-none opacity-0"}`}
          onClick={onCloseDrawer}
          aria-hidden="true"
        />
        <aside
          className={`fixed inset-y-0 right-0 z-40 flex w-[min(380px,100%)] flex-col gap-3.5 overflow-y-auto border-l border-white/10 bg-surface p-4 transition-transform duration-300 ${
            drawerOpen ? "translate-x-0" : "translate-x-full"
          }`}
        >
          <div className="glow-card flex flex-none items-center justify-between rounded-xl py-1.5 pl-4 pr-2">
            <span className="font-display text-base">Widgets</span>
            <button onClick={onCloseDrawer} className="rounded-lg px-2 py-1 text-slate-400 hover:bg-white/5 hover:text-slate-200" aria-label="Close widgets">
              ✕
            </button>
          </div>
          {WIDGET_INFO.map((w) => (
            <div key={w.id} className="max-h-[340px] flex-none">
              {render[w.id]()}
            </div>
          ))}
        </aside>
      </div>
    );
  }

  const column = (side: "left" | "right") => (
    <aside
      className={`rise-in absolute bottom-5 top-4 z-[3] flex flex-col gap-3.5 ${
        side === "left" ? "widget-column-left" : "widget-column-right"
      }`}
      aria-label={side === "left" ? "Activity" : "This run"}
    >
      {SLOTS[side].map((slot) => {
        const id = placed.slots[slot] ?? null;
        const shown = id && id !== drag?.id;
        return (
          <div
            key={slot}
            data-slot={slot}
            // Empty slots are invisible, and faintly tinted while dragging so
            // the places a widget can go are visible.
            className={`flex min-h-0 flex-col rounded-[14px] ${drag && (!id || id === drag.id) ? "bg-white/[0.03] outline-dashed outline-1 outline-[rgba(215,220,227,0.3)]" : ""}`}
            style={{ flex: `${SLOT_FLEX[slot]} 1 0` }}
          >
            {shown && render[id](handleFor(id))}
          </div>
        );
      })}
    </aside>
  );

  return (
    <div ref={rootRef} className={`contents ${drag ? "[&_*]:!cursor-grabbing" : ""}`}>
      {column("left")}
      {column("right")}
      {(Object.entries(placed.free) as [WidgetId, NonNullable<WidgetLayout["free"][WidgetId]>][])
        .filter(([id]) => id !== drag?.id)
        .map(([id, f]) => (
          <div
            key={id}
            className="absolute flex flex-col"
            style={{
              left: area ? clamp(f.x, KEEP_VISIBLE - f.w, area.w - KEEP_VISIBLE) : f.x,
              top: area ? clamp(f.y, 0, area.h - KEEP_VISIBLE) : f.y,
              width: f.w,
              height: f.h,
              zIndex: 4 + f.z,
            }}
          >
            {render[id](handleFor(id))}
          </div>
        ))}
      {drag && (
        <div
          className="widget-dragging absolute left-0 top-0 flex flex-col"
          style={{ transform: `translate3d(${drag.x}px, ${drag.y}px, 0)`, width: drag.w, height: drag.h }}
          aria-hidden="true"
        >
          {render[drag.id]()}
        </div>
      )}
    </div>
  );
}
