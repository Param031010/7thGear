import { useCallback, useEffect, useState, type Dispatch, type SetStateAction } from "react";

// Where each widget is: docked in one of the six home slots (three per side)
// or floating freely inside the chat area. Positions are a viewing
// preference, so they're saved per browser.

export type WidgetId = "stats" | "runs" | "actions" | "plan" | "timeline" | "state";
export type SlotId = "L1" | "L2" | "L3" | "R1" | "R2" | "R3";

export interface FreePlacement {
  x: number;
  y: number;
  w: number;
  h: number;
  z: number;
}

export interface WidgetLayout {
  slots: Partial<Record<SlotId, WidgetId | null>>;
  free: Partial<Record<WidgetId, FreePlacement>>;
}

export const WIDGET_INFO: { id: WidgetId; side: "left" | "right"; name: string }[] = [
  { id: "stats", side: "left", name: "Stats" },
  { id: "runs", side: "left", name: "Recent runs" },
  { id: "actions", side: "left", name: "Actions taken" },
  { id: "plan", side: "right", name: "Current plan" },
  { id: "timeline", side: "right", name: "Execution timeline" },
  { id: "state", side: "right", name: "Agent state" },
];

const WIDGET_IDS = WIDGET_INFO.map((w) => w.id);
const SIDE = Object.fromEntries(WIDGET_INFO.map((w) => [w.id, w.side])) as Record<WidgetId, "left" | "right">;

export const SLOTS: Record<"left" | "right", SlotId[]> = {
  left: ["L1", "L2", "L3"],
  right: ["R1", "R2", "R3"],
};
const ALL_SLOTS: SlotId[] = [...SLOTS.left, ...SLOTS.right];

export const DEFAULT_LAYOUT: WidgetLayout = {
  slots: { L1: "stats", L2: "runs", L3: "actions", R1: "plan", R2: "timeline", R3: "state" },
  free: {},
};

const HOME_SLOT = Object.fromEntries(Object.entries(DEFAULT_LAYOUT.slots).map(([slot, id]) => [id, slot])) as Record<WidgetId, SlotId>;

const STORAGE_KEY = "workflowos.widgetLayout.v1";

// Known widgets only, each in at most one place, or the saved layout is
// thrown away.
const isValid = (layout: unknown): layout is WidgetLayout => {
  if (!layout || typeof layout !== "object") return false;
  const l = layout as WidgetLayout;
  if (typeof l.slots !== "object" || typeof l.free !== "object") return false;
  const placed = [...Object.values(l.slots).filter(Boolean), ...Object.keys(l.free)] as string[];
  return (
    Object.keys(l.slots).every((s) => ALL_SLOTS.includes(s as SlotId)) &&
    placed.every((id) => WIDGET_IDS.includes(id as WidgetId)) &&
    new Set(placed).size === placed.length
  );
};

const load = (): WidgetLayout => {
  try {
    const saved = JSON.parse(localStorage.getItem(STORAGE_KEY) ?? "null");
    return isValid(saved) ? saved : DEFAULT_LAYOUT;
  } catch {
    return DEFAULT_LAYOUT;
  }
};

// Every widget gets a place: its saved slot or free position if it has one,
// otherwise the first empty slot, trying its home slot, then its own
// column, then the other.
export const effectiveLayout = (layout: WidgetLayout): WidgetLayout => {
  const slots: WidgetLayout["slots"] = {};
  for (const s of ALL_SLOTS) slots[s] = layout.slots[s] ?? null;
  const free = { ...layout.free };
  const placed = new Set<string>([...Object.values(slots).filter(Boolean), ...Object.keys(free)] as string[]);
  for (const id of WIDGET_IDS) {
    if (placed.has(id)) continue;
    const other = SIDE[id] === "left" ? "right" : "left";
    const slot = [HOME_SLOT[id], ...SLOTS[SIDE[id]], ...SLOTS[other]].find((s) => s && !slots[s]);
    if (slot) slots[slot] = id;
    placed.add(id);
  }
  return { slots, free };
};

export const isDefaultLayout = (layout: WidgetLayout) =>
  JSON.stringify(effectiveLayout(layout)) === JSON.stringify(effectiveLayout(DEFAULT_LAYOUT));

const placeOf = (layout: WidgetLayout, id: WidgetId): { slot: SlotId } | { free: FreePlacement } | null => {
  const slot = (Object.keys(layout.slots) as SlotId[]).find((s) => layout.slots[s] === id);
  if (slot) return { slot };
  const f = layout.free[id];
  return f ? { free: f } : null;
};

// Put a widget into a slot. Whatever was there takes the moved widget's old
// place (its slot, or its free position), so nothing is ever lost.
export const dockWidget = (layout: WidgetLayout, id: WidgetId, slot: SlotId): WidgetLayout => {
  const from = placeOf(layout, id);
  const occupant = layout.slots[slot];
  const slots = { ...layout.slots };
  const free = { ...layout.free };
  if (from && "slot" in from) slots[from.slot] = null;
  delete free[id];
  slots[slot] = id;
  if (occupant && occupant !== id) {
    if (from && "slot" in from) slots[from.slot] = occupant;
    else if (from && "free" in from) free[occupant] = from.free;
  }
  return { slots, free };
};

export const floatWidget = (layout: WidgetLayout, id: WidgetId, rect: Omit<FreePlacement, "z">): WidgetLayout => {
  const slots = { ...layout.slots };
  for (const s of Object.keys(slots) as SlotId[]) if (slots[s] === id) slots[s] = null;
  const z = Math.max(0, ...Object.values(layout.free).map((f) => f?.z ?? 0)) + 1;
  return { slots, free: { ...layout.free, [id]: { ...rect, z } } };
};

// Back to its home slot, swapping with whatever is there now.
export const sendHome = (layout: WidgetLayout, id: WidgetId): WidgetLayout => dockWidget(layout, id, HOME_SLOT[id]);

export const useWidgetLayout = (): [WidgetLayout, Dispatch<SetStateAction<WidgetLayout>>, () => void] => {
  const [layout, setLayout] = useState<WidgetLayout>(load);
  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(layout));
    } catch {
      // Private mode or storage blocked: the layout just won't persist.
    }
  }, [layout]);
  const reset = useCallback(() => setLayout(DEFAULT_LAYOUT), []);
  return [layout, setLayout, reset];
};

export const useMediaQuery = (query: string) => {
  const [matches, setMatches] = useState(() => window.matchMedia(query).matches);
  useEffect(() => {
    const mql = window.matchMedia(query);
    const onChange = () => setMatches(mql.matches);
    mql.addEventListener("change", onChange);
    return () => mql.removeEventListener("change", onChange);
  }, [query]);
  return matches;
};
