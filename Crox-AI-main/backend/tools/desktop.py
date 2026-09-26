"""Windows desktop automation tools, backed by pywinauto.

This is a fallback mechanism for when no API or browser path exists -- it is
intentionally not the primary automation path (see spec section 15). Real
code (not mocked), but exercised manually rather than in the automated test
suite since it drives real OS windows.
"""

import asyncio
from typing import Optional

from pydantic import BaseModel

from models.schemas import ToolResult
from tools.base import Tool


def _pywinauto():
    import pywinauto  # local import: only required on Windows, keep optional

    return pywinauto


class OpenAppArgs(BaseModel):
    path: str
    args: str = ""


class DesktopOpenAppTool(Tool):
    name = "desktop.open_app"
    description = "Launch a desktop application by executable path."
    input_model = OpenAppArgs

    async def run(self, arguments: OpenAppArgs) -> ToolResult:
        try:
            pywinauto = _pywinauto()
            app = await asyncio.to_thread(pywinauto.Application(backend="uia").start, f"{arguments.path} {arguments.args}".strip())
        except Exception as exc:  # noqa: BLE001
            return ToolResult(success=False, error=str(exc))
        return ToolResult(success=True, data={"launched": arguments.path})


class GetWindowArgs(BaseModel):
    title_re: str


class DesktopGetWindowTool(Tool):
    name = "desktop.get_window"
    description = "Find a top-level window whose title matches a regex."
    input_model = GetWindowArgs

    async def run(self, arguments: GetWindowArgs) -> ToolResult:
        try:
            pywinauto = _pywinauto()
            desktop = pywinauto.Desktop(backend="uia")
            window = await asyncio.to_thread(desktop.window, title_re=arguments.title_re)
            exists = await asyncio.to_thread(window.exists)
        except Exception as exc:  # noqa: BLE001
            return ToolResult(success=False, error=str(exc))
        return ToolResult(success=True, data={"exists": exists})


class DesktopClickArgs(BaseModel):
    title_re: str
    control_name: str


class DesktopClickTool(Tool):
    name = "desktop.click"
    description = "Click a named control inside a window matched by title regex."
    input_model = DesktopClickArgs

    async def run(self, arguments: DesktopClickArgs) -> ToolResult:
        try:
            pywinauto = _pywinauto()
            desktop = pywinauto.Desktop(backend="uia")
            window = desktop.window(title_re=arguments.title_re)
            await asyncio.to_thread(window[arguments.control_name].click_input)
        except Exception as exc:  # noqa: BLE001
            return ToolResult(success=False, error=str(exc))
        return ToolResult(success=True, data={})


class DesktopTypeArgs(BaseModel):
    title_re: str
    text: str


class DesktopTypeTool(Tool):
    name = "desktop.type"
    description = "Type text into the currently focused control of a window matched by title regex."
    input_model = DesktopTypeArgs

    async def run(self, arguments: DesktopTypeArgs) -> ToolResult:
        try:
            pywinauto = _pywinauto()
            desktop = pywinauto.Desktop(backend="uia")
            window = desktop.window(title_re=arguments.title_re)
            await asyncio.to_thread(window.type_keys, arguments.text, with_spaces=True)
        except Exception as exc:  # noqa: BLE001
            return ToolResult(success=False, error=str(exc))
        return ToolResult(success=True, data={})


class DesktopHotkeyArgs(BaseModel):
    keys: str


class DesktopHotkeyTool(Tool):
    name = "desktop.hotkey"
    description = "Send a hotkey combination, e.g. '^s' for Ctrl+S (pywinauto send_keys syntax)."
    input_model = DesktopHotkeyArgs

    async def run(self, arguments: DesktopHotkeyArgs) -> ToolResult:
        try:
            pywinauto = _pywinauto()
            await asyncio.to_thread(pywinauto.keyboard.send_keys, arguments.keys)
        except Exception as exc:  # noqa: BLE001
            return ToolResult(success=False, error=str(exc))
        return ToolResult(success=True, data={})
