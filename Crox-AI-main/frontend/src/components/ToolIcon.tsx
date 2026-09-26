import gmailLogo from "../assets/gmail_logo.png";
import slackLogo from "../assets/slack_logo.png";

export type IconKind = "gmail" | "slack" | "sheets" | "document" | "browser" | "desktop" | "generic";

function DbIcon() {
  return (
    <svg viewBox="0 0 24 24" width="17" height="17" fill="none" aria-hidden="true">
      <ellipse cx="12" cy="5.5" rx="7" ry="2.5" stroke="currentColor" strokeWidth="1.5" />
      <path d="M5 5.5V18.5C5 19.88 8.13 21 12 21C15.87 21 19 19.88 19 18.5V5.5" stroke="currentColor" strokeWidth="1.5" />
      <path d="M5 12C5 13.38 8.13 14.5 12 14.5C15.87 14.5 19 13.38 19 12" stroke="currentColor" strokeWidth="1.5" />
    </svg>
  );
}

function DocIcon() {
  return (
    <svg viewBox="0 0 24 24" width="17" height="17" fill="none" aria-hidden="true">
      <path d="M7 3.5H13.5L18 8V19.5C18 20.05 17.55 20.5 17 20.5H7C6.45 20.5 6 20.05 6 19.5V4.5C6 3.95 6.45 3.5 7 3.5Z" stroke="currentColor" strokeWidth="1.5" strokeLinejoin="round" />
      <path d="M13.5 3.5V8H18" stroke="currentColor" strokeWidth="1.5" strokeLinejoin="round" />
      <path d="M9 13H15M9 16.5H15" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" />
    </svg>
  );
}

function BrowserIcon() {
  return (
    <svg viewBox="0 0 24 24" width="17" height="17" fill="none" aria-hidden="true">
      <circle cx="12" cy="12" r="8.5" stroke="currentColor" strokeWidth="1.5" />
      <path d="M3.5 12H20.5M12 3.5C14 6 15 9 15 12C15 15 14 18 12 20.5C10 18 9 15 9 12C9 9 10 6 12 3.5Z" stroke="currentColor" strokeWidth="1.3" />
    </svg>
  );
}

function DesktopIcon() {
  return (
    <svg viewBox="0 0 24 24" width="17" height="17" fill="none" aria-hidden="true">
      <rect x="3.5" y="4.5" width="17" height="11" rx="1.3" stroke="currentColor" strokeWidth="1.5" />
      <path d="M8.5 20.5H15.5M12 15.5V20.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
    </svg>
  );
}

export function ToolIcon({ icon }: { icon: IconKind }) {
  switch (icon) {
    case "gmail":
      return <img src={gmailLogo} alt="" className="h-[17px] w-[17px] flex-none rounded-[3px] object-cover" />;
    case "slack":
      return <img src={slackLogo} alt="" className="h-[17px] w-[17px] flex-none rounded-[3px] object-cover" />;
    case "sheets":
      return (
        <span className="flex-none text-slate-400">
          <DbIcon />
        </span>
      );
    case "document":
      return (
        <span className="flex-none text-slate-400">
          <DocIcon />
        </span>
      );
    case "browser":
      return (
        <span className="flex-none text-slate-400">
          <BrowserIcon />
        </span>
      );
    case "desktop":
      return (
        <span className="flex-none text-slate-400">
          <DesktopIcon />
        </span>
      );
    default:
      return null;
  }
}
