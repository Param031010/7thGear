import { useState } from "react";
import { AgentBadge } from "./AgentBadge";

export function AskUserCard({
  question,
  options,
  busy,
  onRespond,
}: {
  question: string;
  options: string[];
  busy: boolean;
  onRespond: (answer: string) => void;
}) {
  const [custom, setCustom] = useState("");

  return (
    <div className="glow-card mt-2.5 rounded-xl p-3.5">
      <AgentBadge kind="user" label="Input needed" />
      <p className="mt-2 text-[0.86rem] text-slate-100">{question}</p>
      {options.length > 0 && (
        <div className="mt-2.5 flex flex-wrap gap-1.5">
          {options.map((opt) => (
            <button
              key={opt}
              disabled={busy}
              onClick={() => onRespond(opt)}
              className="hairline rounded-full border px-3 py-1 text-[0.8rem] text-slate-200 transition-colors hover:border-[var(--hairline-strong)] hover:bg-white/5 disabled:opacity-50"
            >
              {opt}
            </button>
          ))}
        </div>
      )}
      <form
        onSubmit={(e) => {
          e.preventDefault();
          if (custom.trim()) onRespond(custom.trim());
        }}
        className="mt-2.5 flex gap-2"
      >
        <input
          value={custom}
          onChange={(e) => setCustom(e.target.value)}
          placeholder="Or type your own answer..."
          disabled={busy}
          className="hairline flex-1 rounded-lg border bg-black/30 px-3 py-1.5 text-[0.82rem] text-slate-100 placeholder:text-slate-600 focus:border-[var(--hairline-strong)] focus:outline-none disabled:opacity-50"
        />
        <button type="submit" disabled={busy || !custom.trim()} className="glow-btn rounded-full px-3.5 py-1.5 text-[0.8rem] font-semibold">
          Send
        </button>
      </form>
    </div>
  );
}
