import { useEffect, useRef, useState } from "react";
import logo from "../assets/logo.png";
import AgentFlowDiagram from "../landing/AgentFlowDiagram";
import { Transcript, type TranscriptLine } from "../landing/Transcript";

const HEADLINE = "Give it a goal. Watch it work.";

interface Stage {
  name: string;
  title: string;
  body: string;
  lines: TranscriptLine[];
}

const STAGES: Stage[] = [
  {
    name: "Goal",
    title: "Say what you want, in plain words",
    body: "Tell WorkFlowOS the outcome you want. Gemini turns it into a short, high-level plan — objectives, not a script to follow blindly.",
    lines: [
      { who: "you", text: "Process today's internship applications." },
      { who: "planner", text: "Goal: process internship applications" },
      { who: "planner", text: "Plan: find applications -> extract candidate -> check tracker -> update -> notify team" },
    ],
  },
  {
    name: "Approve",
    title: "Nothing runs until you say so",
    body: "The plan is shown to you before a single tool call happens. Approve it, reject it, or just read it — the agent waits.",
    lines: [
      { who: "system", text: "Plan ready for review · 5 steps" },
      { who: "you", text: "Approve" },
      { who: "executor", text: "Workflow started" },
    ],
  },
  {
    name: "Execute",
    title: "Real tools, not a simulation",
    body: "The executor calls Gmail, Google Sheets, Slack, and document extraction for real, and reports back exactly what happened.",
    lines: [
      { who: "executor", text: "Calling gmail.search" },
      { who: "executor", text: "gmail.search succeeded — 2 messages" },
      { who: "executor", text: "Calling document.extract_fields" },
      { who: "executor", text: "sheets.search succeeded — found: true" },
    ],
  },
  {
    name: "Replan",
    title: "When reality disagrees with the plan",
    body: "A duplicate record, a missing match, an unexpected result — the agent observes the actual state and decides what to do next, instead of failing or guessing.",
    lines: [
      { who: "replanner", text: "Candidate already exists in the tracker" },
      { who: "replanner", text: "Updating the existing record instead of inserting a duplicate" },
      { who: "executor", text: "sheets.update succeeded" },
      { who: "executor", text: "slack.send succeeded — hiring team notified" },
    ],
  },
];

const prefersReducedMotion = () => window.matchMedia?.("(prefers-reduced-motion: reduce)").matches ?? false;

export default function Landing() {
  const [reducedMotion] = useState(prefersReducedMotion);
  const [stage, setStage] = useState(0);
  const stageRefs = useRef<(HTMLElement | null)[]>([]);
  const storyRef = useRef<HTMLElement>(null);

  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting) {
            const idx = stageRefs.current.findIndex((el) => el === entry.target);
            if (idx >= 0) setStage(idx);
          }
        }
      },
      { threshold: 0.5, rootMargin: "-10% 0px -10% 0px" },
    );
    stageRefs.current.forEach((el) => el && observer.observe(el));
    return () => observer.disconnect();
  }, []);

  const jumpTo = (i: number) => {
    stageRefs.current[i]?.scrollIntoView({ behavior: reducedMotion ? "auto" : "smooth", block: "center" });
  };

  return (
    <div className="silver-bloom relative min-h-screen overflow-x-hidden text-slate-100">
      <div className="grain-overlay" aria-hidden="true" />
      <div className="pointer-events-none fixed inset-0 overflow-hidden" aria-hidden="true">
        <span className="orb orb-1" />
        <span className="orb orb-2" />
        <span className="orb orb-3" />
        <span className="orb orb-4" />
        <span className="orb orb-5" />
      </div>

      <header className="relative z-10 flex items-center justify-between px-6 py-5 sm:px-10">
        <a href="#/" className="flex items-center gap-2.5">
          <img src={logo} alt="" className="glow-logo h-8 w-8 rounded-lg" />
          <span className="glow-text font-display text-lg font-medium tracking-tight">WorkFlowOS</span>
        </a>
        <a
          href="#/app"
          className="hairline rounded-xl border px-4 py-2 text-sm font-medium text-slate-100 transition-all hover:border-[var(--hairline-strong)] hover:bg-white/5 hover:shadow-[0_0_18px_-4px_rgba(215,220,227,0.45)]"
        >
          Open the app
        </a>
      </header>

      <main className="relative z-10">
        <section className="mx-auto flex max-w-3xl flex-col items-center px-6 pb-24 pt-16 text-center sm:pt-24">
          <h1 className="glow-text font-display text-4xl font-medium leading-tight tracking-tight sm:text-6xl">
            {HEADLINE.split(" ").map((word, w, words) => {
              const offset = words.slice(0, w).join(" ").length + (w ? 1 : 0);
              return (
                <span key={w} className="inline-block whitespace-nowrap">
                  {word.split("").map((ch, i) => (
                    <span
                      key={i}
                      className="landing-char"
                      style={{ animationDelay: reducedMotion ? "0ms" : `${350 + (offset + i) * 40}ms` }}
                    >
                      {ch}
                    </span>
                  ))}
                  {w < words.length - 1 ? " " : ""}
                </span>
              );
            })}
          </h1>
          <p className="mt-6 max-w-xl text-balance text-base text-slate-400 sm:text-lg">
            WorkFlowOS turns a goal into a plan, runs it against real Gmail, Sheets, and Slack, and replans the moment
            reality doesn't match what was expected — every change approved by you first.
          </p>
          <div className="mt-8 flex flex-wrap items-center justify-center gap-3">
            <a
              href="#/app"
              className="glow-btn rounded-xl px-5 py-2.5 text-sm font-semibold"
            >
              Try WorkFlowOS
            </a>
            <button
              type="button"
              onClick={() => jumpTo(0)}
              className="hairline rounded-xl border px-5 py-2.5 text-sm font-medium text-slate-200 transition-all hover:border-[var(--hairline-strong)] hover:bg-white/5 hover:shadow-[0_0_18px_-4px_rgba(215,220,227,0.45)]"
            >
              See how it works
            </button>
          </div>
        </section>

        <section ref={storyRef} className="relative mx-auto max-w-5xl px-6 pb-28">
          <nav aria-label="How WorkFlowOS works" className="sticky top-6 z-10 mb-10 flex justify-center gap-2">
            {STAGES.map((s, i) => (
              <button
                key={s.name}
                type="button"
                onClick={() => jumpTo(i)}
                className={`rounded-full border px-3 py-1.5 text-xs font-medium backdrop-blur-md transition-all ${
                  i === stage
                    ? "border-[var(--hairline-strong)] bg-white/10 text-white shadow-[0_0_18px_-4px_rgba(215,220,227,0.55)]"
                    : "border-[var(--hairline)] bg-black/40 text-slate-400 hover:text-slate-200"
                }`}
              >
                {s.name}
              </button>
            ))}
          </nav>

          <div className="space-y-28">
            {STAGES.map((s, i) => (
              <article
                key={s.name}
                ref={(el) => {
                  stageRefs.current[i] = el;
                }}
                className="grid gap-8 sm:grid-cols-2 sm:items-center"
              >
                <div>
                  <span className="glow-title text-xs font-semibold uppercase tracking-[0.1em]">
                    {String(i + 1).padStart(2, "0")} · {s.name}
                  </span>
                  <h2 className="mt-2 font-display text-2xl font-medium">{s.title}</h2>
                  <p className="mt-3 text-sm leading-relaxed text-slate-400">{s.body}</p>
                </div>
                <div className="glow-card rounded-2xl p-5">
                  <Transcript lines={s.lines} play={i === stage} reducedMotion={reducedMotion} />
                </div>
              </article>
            ))}
          </div>
        </section>

        <section className="mx-auto max-w-4xl px-6 pb-28 text-center">
          <h2 className="font-display text-2xl font-medium sm:text-3xl">Who does what</h2>
          <p className="mx-auto mt-3 max-w-xl text-sm text-slate-400">
            The planner drafts the plan, you approve it, and one agent takes it from there — deciding the next step
            after every single result, calling a tool, or stopping to ask you when it can't safely decide on its own.
          </p>
          <div className="mt-12">
            <AgentFlowDiagram reducedMotion={reducedMotion} />
          </div>
        </section>

        <section className="border-t border-[var(--hairline)] px-6 py-20 text-center">
          <h2 className="font-display text-2xl font-medium sm:text-3xl">Give it a goal</h2>
          <p className="mx-auto mt-3 max-w-md text-sm text-slate-400">
            Approve the plan, watch it run, and change nothing until you say so.
          </p>
          <a
            href="#/app"
            className="glow-btn mt-6 inline-block rounded-xl px-5 py-2.5 text-sm font-semibold"
          >
            Try WorkFlowOS
          </a>
        </section>
      </main>

      <footer className="relative z-10 flex items-center justify-between border-t border-[var(--hairline)] px-6 py-6 text-xs text-slate-500 sm:px-10">
        <span>WorkFlowOS</span>
        <span>Goal &rarr; Plan &rarr; Execute &rarr; Replan &rarr; Complete</span>
      </footer>
    </div>
  );
}
