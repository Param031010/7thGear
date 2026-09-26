// A live/in-progress status gets a brighter dot and text; everything else is
// plain -- the word itself ("Failed", "Completed") carries the meaning, not
// a color.
const LIVE = new Set(["running", "awaiting_approval", "awaiting_user_input", "paused"]);

export function StatusBadge({ status }: { status: string }) {
  const live = LIVE.has(status);
  return (
    <span
      className={`inline-flex flex-none items-center gap-1.5 whitespace-nowrap rounded-full border px-2 py-0.5 text-[0.7rem] font-medium capitalize ${
        live
          ? "border-[var(--hairline-strong)] text-[var(--silver-bright)] shadow-[0_0_12px_-3px_rgba(215,220,227,0.5)]"
          : "border-[var(--hairline)] text-slate-400"
      }`}
    >
      <span
        className={`h-1.5 w-1.5 flex-none rounded-full ${
          live ? "animate-pulse bg-[var(--silver-bright)] shadow-[0_0_6px_rgba(215,220,227,0.9)]" : "bg-slate-500"
        }`}
      />
      {status.replace(/_/g, " ")}
    </span>
  );
}
