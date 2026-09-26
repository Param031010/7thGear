"""Desktop shell: runs the FastAPI backend in a background thread and shows
the built frontend in a native OS webview (WebView2 on Windows, WebKit on
macOS, GTK/WebKitGTK on Linux) via pywebview. Replaces the earlier Electron
shell -- same backend, same built frontend/dist, no Node/Chromium runtime.
"""

import argparse
import sys
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

import uvicorn
import webview

from config import get_settings

FRONTEND_DIST = Path(__file__).resolve().parent.parent / "frontend" / "dist" / "index.html"
DEV_SERVER_URL = "http://127.0.0.1:5173/"


def _run_backend(host: str, port: int) -> None:
    uvicorn.run("main:app", host=host, port=port, log_level="warning")


def _wait_for_backend(url: str, timeout: float = 20.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=1):
                return True
        except (urllib.error.URLError, TimeoutError, ConnectionError):
            time.sleep(0.3)
    return False


def main() -> None:
    parser = argparse.ArgumentParser(description="WorkFlowOS desktop shell")
    parser.add_argument("--dev", action="store_true", help=f"Load the Vite dev server ({DEV_SERVER_URL}) instead of the built frontend")
    parser.add_argument("--selftest", action="store_true", help="Start the backend and verify everything is wired up, then exit (no GUI window)")
    args = parser.parse_args()

    settings = get_settings()
    health_url = f"http://{settings.backend_host}:{settings.backend_port}/health"

    if not args.dev and not FRONTEND_DIST.exists():
        print(f"Frontend build not found at {FRONTEND_DIST}\nRun 'npm run build' in frontend/ first, or pass --dev to use the Vite dev server.")
        sys.exit(1)

    thread = threading.Thread(target=_run_backend, args=(settings.backend_host, settings.backend_port), daemon=True)
    thread.start()

    if not _wait_for_backend(health_url):
        print(f"Backend didn't come up at {health_url} in time.")
        sys.exit(1)
    print(f"Backend is up at {health_url} (demo_mode={settings.demo_mode})")

    if args.selftest:
        print("Selftest OK -- backend started, frontend build present. Exiting without opening a window.")
        return

    target = DEV_SERVER_URL if args.dev else str(FRONTEND_DIST)
    webview.create_window(
        "WorkFlowOS",
        target,
        width=1360,
        height=860,
        min_size=(1024, 680),
        background_color="#08090a",
    )
    webview.start()


if __name__ == "__main__":
    main()
