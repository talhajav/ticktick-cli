"""Shared test fixtures for ticktick-cli integration tests.

All tests use live TickTick V2 API credentials. Test artifacts are isolated
in a dedicated sandbox project that is cleaned up after the test session.
"""

from __future__ import annotations

import pytest

from unittest.mock import MagicMock

from click.testing import CliRunner

from ticktick_cli.api.client import TickTickClient
from ticktick_cli.config import load_auth
from ticktick_cli.api.v2 import V2Client, _generate_object_id

TEST_PROJECT_NAME = "__hermes_test_sandbox__"


@pytest.fixture
def runner() -> CliRunner:
    """Click CliRunner for testing CLI commands."""
    return CliRunner()


@pytest.fixture(scope="session")
def client() -> V2Client:
    """Authenticated V2 client using stored credentials."""
    auth = load_auth()
    client = V2Client()
    client.set_session(auth["v2"]["cookies"])
    return client


@pytest.fixture(scope="session")
def test_project(client: V2Client) -> str:
    """Create/retrieve a sandbox project. Cleaned up after all tests."""
    sync = client.sync()
    for p in sync.get("projectProfiles", []):
        if p.get("name") == TEST_PROJECT_NAME:
            pid = p["id"]
            break
    else:
        pid = _generate_object_id()
        client.batch_projects(
            add=[{
                "id": pid,
                "name": TEST_PROJECT_NAME,
                "color": "#CCCCCC",
                "kind": "TASK",
                "viewMode": "list",
            }]
        )

    yield pid

    # Cleanup: delete all tasks in the project, then the project itself
    try:
        # Get all active tasks in the project
        all_tasks = client.get_all_tasks()
        deletes = []
        for t in all_tasks:
            if t.get("projectId") == pid:
                deletes.append({"taskId": t["id"], "projectId": pid})
        if deletes:
            client.batch_tasks(delete=deletes)
        # Also clean up completed tasks
        from datetime import datetime, timedelta
        completed = client.get_completed_tasks(
            datetime.now() - timedelta(days=30), datetime.now(), limit=1000
        )
        completed_deletes = []
        for t in completed:
            if t.get("projectId") == pid:
                completed_deletes.append({"taskId": t["id"], "projectId": pid})
        if completed_deletes:
            client.batch_tasks(delete=completed_deletes)
        # Delete the project
        client.batch_projects(delete=[pid])
    except Exception:
        pass  # Best-effort cleanup
