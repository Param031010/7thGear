import { useEffect, useRef, useState } from "react";

const ACCENT = "#c7cdd6";

// Matches the real orchestrator loop: there's no separate "executor" agent
// with its own judgment -- one call (decide_next_action) runs before every
// tool call, decides whether to continue, replan, or stop and ask, then a
// tool actually runs. The two-way arrow into "Ask you" is a real, demoed
// path (e.g. guessing the wrong Slack channel and being corrected).
const AGENTS = {
  planner: { name: "Planner", role: "Drafts the high-level plan from your goal" },
  you: { name: "You", role: "Approve the plan before anything runs" },
  loop: { name: "Agent", role: "Decides the next step and runs it, every time" },
  tools: { name: "Tools", role: "Gmail, Sheets, Slack, documents, browser" },
  askUser: { name: "Ask you", role: "Steps in when it can't safely decide on its own" },
};

type NodeId = keyof typeof AGENTS;

const VIEWBOX: [number, number] = [640, 460];
const NODES: Record<NodeId, [number, number]> = {
  planner: [320, 40],
  you: [320, 150],
  loop: [320, 270],
  tools: [520, 350],
  askUser: [120, 350],
};

const EDGES: Record<string, { d: string; label: [number, number]; text: string; dashed?: boolean }> = {
  "planner-you": { d: "M320,70 L320,120", label: [345, 98], text: "you review it" },
  "you-loop": { d: "M320,178 L320,238", label: [345, 210], text: "approved" },
  "loop-tools": { d: "M362,288 C440,310 480,315 503,328", label: [452, 296], text: "runs a step" },
  "loop-askUser": { d: "M278,288 C200,310 160,315 137,328", label: [188, 296], text: "can't decide", dashed: true },
};

const CYCLE_S = 10;
const PULSES: { edge: keyof typeof EDGES; from: number; to: number; at: NodeId; reverse?: boolean; caption: string }[] = [
  { edge: "planner-you", from: 0.0, to: 0.1, at: "you", caption: "The planner drafts a high-level plan from your goal" },
  { edge: "you-loop", from: 0.12, to: 0.22, at: "loop", caption: "You approve it, and one agent takes over from here" },
  { edge: "loop-tools", from: 0.24, to: 0.36, at: "tools", caption: "It decides the next step and calls a real tool" },
  { edge: "loop-tools", from: 0.38, to: 0.5, at: "loop", reverse: true, caption: "It observes exactly what happened, not what was expected" },
  { edge: "loop-askUser", from: 0.52, to: 0.64, at: "askUser", caption: "When it can't safely decide, it asks you instead of guessing" },
  { edge: "loop-askUser", from: 0.66, to: 0.78, at: "loop", reverse: true, caption: "Your answer feeds back in, and it carries on" },
  { edge: "loop-tools", from: 0.8, to: 0.92, at: "tools", caption: "...calling tools and checking results until the goal is done" },
];

export default function AgentFlowDiagram({ reducedMotion }: { reducedMotion: boolean }) {
  const rootRef = useRef<HTMLDivElement>(null);
  const [visible, setVisible] = useState(reducedMotion);
  const [slot, setSlot] = useState(-1);
  const mountedAt = useRef<number | null>(null);
  const [vw, vh] = VIEWBOX;

  useEffect(() => {
    if (visible || !rootRef.current) return;
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setVisible(true);
          observer.disconnect();
        }
      },
      { threshold: 0.3 },
    );
    observer.observe(rootRef.current);
    return () => observer.disconnect();
  }, [visible]);

  useEffect(() => {
    if (!visible || reducedMotion) return;
    mountedAt.current = performance.now();
    const timer = setInterval(() => {
      if (mountedAt.current == null) return;
      const phase = (((performance.now() - mountedAt.current) / 1000) % CYCLE_S) / CYCLE_S;
      setSlot(PULSES.findIndex((p) => phase >= p.from && phase <= p.to + 0.02));
    }, 100);
    return () => clearInterval(timer);
  }, [visible, reducedMotion]);

  const current = slot >= 0 ? PULSES[slot] : null;
  const activeAgent = current?.at ?? null;
  const activeEdge = current?.edge ?? null;
  const order: NodeId[] = ["planner", "you", "loop", "tools", "askUser"];

  return (
    <div ref={rootRef} className={visible ? "opacity-100" : "opacity-0"} style={{ transition: "opacity 600ms ease" }}>
      <div className="relative mx-auto" style={{ aspectRatio: `${vw} / ${vh}`, maxWidth: 720 }}>
        <svg viewBox={`0 0 ${vw} ${vh}`} className="absolute inset-0 h-full w-full" aria-hidden="true">
          {Object.entries(EDGES).map(([id, edge]) => (
            <g key={id}>
              <path
                id={`agent-edge-${id}`}
                d={edge.d}
                fill="none"
                stroke={ACCENT}
                strokeWidth={activeEdge === id ? 2.4 : 1.4}
                strokeDasharray={edge.dashed ? "5 5" : undefined}
                opacity={activeEdge === id ? 1 : 0.35}
                style={{ transition: "opacity 200ms, stroke-width 200ms" }}
              />
              <text x={edge.label[0]} y={edge.label[1]} fill="#6b7280" fontSize="11" textAnchor="middle">
                {edge.text}
              </text>
            </g>
          ))}

          {visible &&
            !reducedMotion &&
            PULSES.map((p, i) => {
              const keyTimes = `0;${p.from};${p.to};1`;
              const opacityValues = "0;0;1;1;0;0";
              const opacityKeyTimes = `0;${p.from};${p.from + 0.005};${p.to - 0.005};${p.to};1`;
              const keyPoints = p.reverse ? "1;1;0;0" : "0;0;1;1";
              return (
                <circle key={i} r="4.5" fill={ACCENT} opacity="0">
                  <animateMotion dur={`${CYCLE_S}s`} begin="0s" repeatCount="indefinite" keyPoints={keyPoints} keyTimes={keyTimes} calcMode="linear">
                    <mpath href={`#agent-edge-${p.edge}`} />
                  </animateMotion>
                  <animate
                    attributeName="opacity"
                    dur={`${CYCLE_S}s`}
                    begin="0s"
                    repeatCount="indefinite"
                    values={opacityValues}
                    keyTimes={opacityKeyTimes}
                  />
                </circle>
              );
            })}
        </svg>

        {order.map((key) => {
          const agent = AGENTS[key];
          const [x, y] = NODES[key];
          const active = activeAgent === key;
          return (
            <div
              key={key}
              className="absolute flex w-36 -translate-x-1/2 -translate-y-1/2 flex-col items-center gap-1 rounded-xl border px-3 py-2 text-center transition-all duration-200"
              style={{
                left: `${(x / vw) * 100}%`,
                top: `${(y / vh) * 100}%`,
                borderColor: active ? "rgba(244, 246, 249, 0.8)" : "rgba(215, 220, 227, 0.28)",
                background: active ? "rgba(215, 220, 227, 0.1)" : "rgba(12, 13, 15, 0.8)",
                boxShadow: active
                  ? "inset 0 1px 0 rgba(255,255,255,0.12), 0 0 32px rgba(215, 220, 227, 0.45)"
                  : "inset 0 1px 0 rgba(255,255,255,0.07), 0 0 20px -8px rgba(215, 220, 227, 0.3)",
              }}
            >
              <span className={`text-xs font-semibold ${active ? "text-white" : "text-slate-300"}`}>{agent.name}</span>
              <span className="text-[0.65rem] leading-tight text-slate-500">{agent.role}</span>
            </div>
          );
        })}
      </div>

      <p className="mt-6 text-center text-sm text-slate-400" aria-live="off">
        {reducedMotion
          ? "The planner drafts a plan, you approve it, then one agent decides the next step after every result -- calling a tool, or stopping to ask you -- until the goal is done."
          : current?.caption || "Follow a goal through WorkFlowOS"}
      </p>
    </div>
  );
}
