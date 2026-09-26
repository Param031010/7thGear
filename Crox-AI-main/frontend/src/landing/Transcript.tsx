import { useEffect, useRef, useState } from "react";
import { AgentBadge, type AgentKind } from "../components/AgentBadge";

export interface TranscriptLine {
  who: AgentKind | "you";
  text: string;
  tone?: "add" | "del";
}

const CHAR_MS = 16;
const LINE_PAUSE_MS = 320;

// Prints a fake (but representative) agent transcript line by line, the way
// activity streams in the real chat. Plays once, the first time its stage
// is active; reduced-motion shows everything at once.
export function Transcript({ lines, play, reducedMotion }: { lines: TranscriptLine[]; play: boolean; reducedMotion: boolean }) {
  const [shown, setShown] = useState(() => (reducedMotion ? { line: lines.length, chars: 0 } : { line: 0, chars: 0 }));
  const started = useRef(reducedMotion);

  useEffect(() => {
    if (!play || started.current) return;
    started.current = true;
    let line = 0;
    let chars = 0;
    let timer: ReturnType<typeof setTimeout>;
    const tick = () => {
      if (line >= lines.length) return;
      const text = lines[line].text;
      if (chars < text.length) {
        chars = Math.min(text.length, chars + 2);
        setShown({ line, chars });
        timer = setTimeout(tick, CHAR_MS);
      } else {
        line += 1;
        chars = 0;
        setShown({ line, chars });
        timer = setTimeout(tick, LINE_PAUSE_MS);
      }
    };
    timer = setTimeout(tick, 250);
    return () => clearTimeout(timer);
  }, [play, lines]);

  return (
    <ol className="space-y-1.5 font-mono text-[0.8rem]" aria-hidden="true">
      {lines.map((l, i) => {
        if (i > shown.line) return null;
        const text = i < shown.line ? l.text : l.text.slice(0, shown.chars);
        const typing = i === shown.line && shown.line < lines.length;
        const isDiff = Boolean(l.tone);
        return (
          <li key={i} className="flex items-start gap-2 text-slate-300">
            {!isDiff && (l.who === "you" ? <AgentBadge kind="system" label="You" /> : <AgentBadge kind={l.who} />)}
            <span className={isDiff ? "pl-2" : ""}>
              {l.tone === "add" ? "+ " : l.tone === "del" ? "- " : ""}
              {text}
              {typing && <span className="type-caret" />}
            </span>
          </li>
        );
      })}
    </ol>
  );
}
