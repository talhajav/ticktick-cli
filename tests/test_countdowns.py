"""Integration tests for countdown commands (Phase 2.1)."""

from __future__ import annotations

from ticktick_cli.api.v2 import _generate_object_id


class TestCountdownCRUD:
    """Tests for countdown create, list, edit, delete."""

    def test_create_simple_countdown(self, client):
        """Create a basic countdown and verify it appears in list."""
        cid = _generate_object_id()
        client.batch_countdowns(add=[{
            "id": cid,
            "name": "Test Countdown",
            "date": 20261225,
            "type": 0,
        }])
        all_items = client.get_countdowns()
        found = next((c for c in all_items if c.get("id") == cid), None)
        assert found is not None, "Countdown not found after creation"
        # Cleanup
        client.batch_countdowns(delete=[cid])

    def test_create_birthday(self, client):
        """Create a birthday-type countdown with ignoreYear."""
        cid = _generate_object_id()
        client.batch_countdowns(add=[{
            "id": cid,
            "name": "Test Birthday",
            "date": 19950820,
            "type": 2,
            "ignoreYear": True,
            "showAge": True,
        }])
        found = next(
            (c for c in client.get_countdowns() if c.get("id") == cid), None
        )
        assert found is not None
        assert found.get("type") == 2
        assert found.get("ignoreYear") is True
        client.batch_countdowns(delete=[cid])

    def test_update_countdown_name(self, client):
        """Rename a countdown."""
        cid = _generate_object_id()
        client.batch_countdowns(add=[{
            "id": cid, "name": "Original", "date": 20261225, "type": 0,
        }])
        client.batch_countdowns(update=[{"id": cid, "name": "Renamed"}])
        found = next(
            (c for c in client.get_countdowns() if c.get("id") == cid), None
        )
        assert found is not None
        assert found.get("name") == "Renamed"
        client.batch_countdowns(delete=[cid])

    def test_delete_countdown(self, client):
        """Delete a countdown and verify it's gone."""
        cid = _generate_object_id()
        client.batch_countdowns(add=[{
            "id": cid, "name": "To Delete", "date": 20261225, "type": 0,
        }])
        client.batch_countdowns(delete=[cid])
        all_items = client.get_countdowns()
        found = next((c for c in all_items if c.get("id") == cid), None)
        assert found is None, "Countdown should be deleted"

    def test_list_countdowns(self, client):
        """List returns array (may be empty)."""
        items = client.get_countdowns()
        assert isinstance(items, list)

    def test_create_with_reminder(self, client):
        """Create a countdown with a reminder."""
        cid = _generate_object_id()
        client.batch_countdowns(add=[{
            "id": cid,
            "name": "Reminder Countdown",
            "date": 20261225,
            "type": 0,
            "reminders": [{"id": _generate_object_id(), "trigger": "TRIGGER:-P1D"}],
        }])
        found = next(
            (c for c in client.get_countdowns() if c.get("id") == cid), None
        )
        assert found is not None
        reminders = found.get("reminders", [])
        assert len(reminders) >= 1
        client.batch_countdowns(delete=[cid])

    def test_edit_sort_order(self, client):
        """Edit a countdown's sortOrder."""
        cid = _generate_object_id()
        client.batch_countdowns(add=[{
            "id": cid, "name": "Sort Test", "date": 20261225, "type": 0,
        }])
        client.batch_countdowns(update=[{"id": cid, "sortOrder": 42}])
        found = next(
            (c for c in client.get_countdowns() if c.get("id") == cid), None
        )
        assert found is not None
        assert found.get("sortOrder") == 42
        client.batch_countdowns(delete=[cid])

    def test_edit_pin(self, client):
        """Pin and unpin a countdown."""
        cid = _generate_object_id()
        client.batch_countdowns(add=[{
            "id": cid, "name": "Pin Test", "date": 20261225, "type": 0,
        }])
        client.batch_countdowns(update=[{"id": cid, "pinned": True}])
        found = next(
            (c for c in client.get_countdowns() if c.get("id") == cid), None
        )
        assert found is not None
        assert found.get("pinned") is True
        client.batch_countdowns(delete=[cid])
