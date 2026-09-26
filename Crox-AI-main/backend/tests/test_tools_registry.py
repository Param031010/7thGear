from tools.base import ToolArgumentError
from tools.registry import get_tool, get_tool_registry


def test_registry_contains_expected_demo_tools():
    registry = get_tool_registry()
    for name in ["gmail.search", "gmail.read", "gmail.download_attachment", "sheets.search", "sheets.insert",
                 "sheets.update", "slack.send", "document.extract_text", "document.extract_fields", "ask_user"]:
        assert name in registry, f"missing tool {name}"


def test_get_tool_returns_none_for_unknown_name():
    assert get_tool("shell.execute") is None


def test_tool_spec_exposes_schema_not_code():
    tool = get_tool("sheets.insert")
    spec = tool.spec()
    assert spec["name"] == "sheets.insert"
    assert "arguments_schema" in spec
    assert "properties" in spec["arguments_schema"]


def test_validate_arguments_rejects_missing_required_field():
    tool = get_tool("sheets.insert")
    try:
        tool.validate_arguments({"name": "No Email"})
    except ToolArgumentError:
        pass
    else:
        raise AssertionError("expected ToolArgumentError for missing required 'email'")
