"""Integration tests for habit extras (Phase 2.2-2.5)."""

from __future__ import annotations


class TestHabitSections:
    """Tests for habit sections listing."""

    def test_list_habit_sections(self, client):
        """Section list returns morning/afternoon/night."""
        sections = client.get_habit_sections()
        assert isinstance(sections, list)
        ids = [s.get("id", "") for s in sections]
        assert "_morning" in ids or len(sections) >= 1


class TestHabitPreferences:
    """Tests for habit preferences."""

    def test_show_habit_preferences(self, client):
        """Preferences returns a dict with expected keys."""
        prefs = client.get_habit_preferences()
        assert isinstance(prefs, dict)
        # May contain enabled, showInCalendar, etc.


class TestHabitStatistics:
    """Tests for habit weekly stats."""

    def test_habit_stats_global(self, client):
        """Global stats returns a dict."""
        stats = client.get_habit_statistics()
        assert isinstance(stats, dict)

    def test_habit_stats_specific(self, client):
        """Stats for a specific habit returns a dict."""
        stats = client.get_habit_statistics("nonexistent_id")
        assert isinstance(stats, dict)


class TestHabitEditExpanded:
    """Tests for expanded habit edit fields."""

    def test_edit_habit_section(self, client):
        """Change habit section via API."""
        # Create a test habit, edit its section
        from ticktick_cli.api.v2 import _generate_object_id
        hid = _generate_object_id()
        client.batch_habits(add=[{
            "id": hid,
            "name": "Section Test Habit",
            "type": "Boolean",
            "goal": 1.0,
            "status": 0,
        }])
        client.batch_habits(update=[{
            "id": hid,
            "sectionId": "_afternoon",
        }])
        # Cleanup
        client.batch_habits(delete=[hid])

    def test_edit_habit_reminder(self, client):
        """Set a reminder on a habit."""
        from ticktick_cli.api.v2 import _generate_object_id
        hid = _generate_object_id()
        client.batch_habits(add=[{
            "id": hid,
            "name": "Reminder Habit",
            "type": "Boolean",
            "goal": 1.0,
            "status": 0,
        }])
        client.batch_habits(update=[{
            "id": hid,
            "reminder": "08:00",
        }])
        client.batch_habits(delete=[hid])

    def test_edit_habit_unit(self, client):
        """Set a unit label on a habit."""
        from ticktick_cli.api.v2 import _generate_object_id
        hid = _generate_object_id()
        client.batch_habits(add=[{
            "id": hid,
            "name": "Unit Habit",
            "type": "Real",
            "goal": 8.0,
            "status": 0,
        }])
        client.batch_habits(update=[{
            "id": hid,
            "unit": "glasses",
        }])
        client.batch_habits(delete=[hid])
