"""Playwright-backed browser automation tools.

Real (not mocked) -- Playwright doesn't need external credentials, just
`playwright install chromium` once. A single browser/page is lazily started
and reused across calls within a run. Prefer semantic selectors
(get_by_role/get_by_text) over coordinates wherever the caller can provide them.
"""

from typing import Optional

from pydantic import BaseModel

from models.schemas import ToolResult
from tools.base import Tool

_playwright = None
_browser = None
_page = None


async def _get_page():
    global _playwright, _browser, _page
    if _page is not None:
        return _page
    from playwright.async_api import async_playwright

    _playwright = await async_playwright().start()
    _browser = await _playwright.chromium.launch(headless=True)
    _page = await _browser.new_page()
    return _page


async def shutdown_browser() -> None:
    global _playwright, _browser, _page
    if _browser is not None:
        await _browser.close()
    if _playwright is not None:
        await _playwright.stop()
    _playwright = _browser = _page = None


class NavigateArgs(BaseModel):
    url: str


class BrowserNavigateTool(Tool):
    name = "browser.navigate"
    description = "Navigate the browser to a URL."
    input_model = NavigateArgs

    async def run(self, arguments: NavigateArgs) -> ToolResult:
        page = await _get_page()
        try:
            await page.goto(arguments.url)
        except Exception as exc:  # noqa: BLE001 - surface as a tool failure, not a crash
            return ToolResult(success=False, error=str(exc))
        return ToolResult(success=True, data={"url": page.url, "title": await page.title()})


class ClickArgs(BaseModel):
    role: Optional[str] = None
    name: Optional[str] = None
    selector: Optional[str] = None


class BrowserClickTool(Tool):
    name = "browser.click"
    description = "Click an element, preferring role+name (e.g. role='button', name='Submit') over a raw CSS selector."
    input_model = ClickArgs

    async def run(self, arguments: ClickArgs) -> ToolResult:
        page = await _get_page()
        try:
            if arguments.role and arguments.name:
                await page.get_by_role(arguments.role, name=arguments.name).click()
            elif arguments.selector:
                await page.click(arguments.selector)
            else:
                return ToolResult(success=False, error="provide either role+name or selector")
        except Exception as exc:  # noqa: BLE001
            return ToolResult(success=False, error=str(exc))
        return ToolResult(success=True, data={})


class TypeArgs(BaseModel):
    role: Optional[str] = None
    name: Optional[str] = None
    selector: Optional[str] = None
    text: str


class BrowserTypeTool(Tool):
    name = "browser.type"
    description = "Type text into an input, preferring role+name over a raw CSS selector."
    input_model = TypeArgs

    async def run(self, arguments: TypeArgs) -> ToolResult:
        page = await _get_page()
        try:
            if arguments.role and arguments.name:
                await page.get_by_role(arguments.role, name=arguments.name).fill(arguments.text)
            elif arguments.selector:
                await page.fill(arguments.selector, arguments.text)
            else:
                return ToolResult(success=False, error="provide either role+name or selector")
        except Exception as exc:  # noqa: BLE001
            return ToolResult(success=False, error=str(exc))
        return ToolResult(success=True, data={})


class GetTextArgs(BaseModel):
    selector: Optional[str] = None


class BrowserGetTextTool(Tool):
    name = "browser.get_text"
    description = "Read visible text from the page, or from a specific selector if provided."
    input_model = GetTextArgs

    async def run(self, arguments: GetTextArgs) -> ToolResult:
        page = await _get_page()
        try:
            if arguments.selector:
                text = await page.inner_text(arguments.selector)
            else:
                text = await page.inner_text("body")
        except Exception as exc:  # noqa: BLE001
            return ToolResult(success=False, error=str(exc))
        return ToolResult(success=True, data={"text": text})
