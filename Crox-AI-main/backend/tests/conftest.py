import os

# Force DEMO_MODE regardless of the developer's real .env -- tests must never
# depend on (or accidentally hit) live Gmail/Sheets/Slack credentials. This
# has to run before config.py's load_dotenv() call, which won't override an
# already-set environment variable, so it must be the first thing this file
# does, and this file must be the first backend module pytest imports (which
# pytest guarantees for conftest.py).
os.environ["DEMO_MODE"] = "true"

import pytest

from config import get_settings
from tools.mock.mock_sheets import reset_tracker
from tools.mock import mock_slack
from tools.registry import get_tool_registry


@pytest.fixture(autouse=True)
def _reset_demo_state():
    get_settings.cache_clear()
    get_tool_registry.cache_clear()
    reset_tracker()
    mock_slack.sent_messages.clear()
    yield
