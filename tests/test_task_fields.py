"""Integration tests for new task fields (Phase 1.1-1.4)."""

from __future__ import annotations

import pytest

from ticktick_cli.api.v2 import _generate_object_id


class TestTaskAssignee:
    """Tests for the --assignee field."""

    def test_create_task_with_assignee(self, client, test_project):
        """Create a task with --assignee and verify via API."""
        task_id = _generate_object_id()
        client.batch_tasks(add=[{
            "id": task_id,
            "projectId": test_project,
            "title": "Assign Test",
            "assignee": 122781208,  # Talha
            "content": "",
            "kind": "TEXT",
            "status": 0,
            "priority": 0,
            "tags": [],
            "items": [],
            "reminders": [],
            "startDate": None,
            "dueDate": None,
            "isAllDay": False,
            "timeZone": "America/Los_Angeles",
        }])
        task = client.get_task(task_id)
        assert task["id"] == task_id
        assert task.get("assignee") == 122781208

    def test_assignee_shows_in_get_task(self, client, test_project):
        """Task retrieved via get_task includes assignee field."""
        task_id = _generate_object_id()
        client.batch_tasks(add=[{
            "id": task_id,
            "projectId": test_project,
            "title": "Assignee Visibility Test",
            "assignee": 122781208,
            "content": "",
            "kind": "TEXT",
            "status": 0,
            "priority": 0,
            "tags": [],
            "items": [],
            "reminders": [],
            "startDate": None,
            "dueDate": None,
            "isAllDay": False,
            "timeZone": "America/Los_Angeles",
        }])
        task = client.get_task(task_id)
        assert "assignee" in task


class TestTaskKind:
    """Tests for --kind (CHECKLIST vs TEXT)."""

    def test_create_checklist_task(self, client, test_project):
        """--kind CHECKLIST creates a checklist-type task."""
        task_id = _generate_object_id()
        client.batch_tasks(add=[{
            "id": task_id,
            "projectId": test_project,
            "title": "Checklist Test",
            "kind": "CHECKLIST",
            "content": "",
            "status": 0,
            "priority": 0,
            "tags": [],
            "items": [],
            "reminders": [],
            "startDate": None,
            "dueDate": None,
            "isAllDay": False,
            "timeZone": "America/Los_Angeles",
        }])
        task = client.get_task(task_id)
        assert task.get("kind") == "CHECKLIST"

    def test_create_text_task_default(self, client, test_project):
        """Default kind should be TEXT or absent."""
        task_id = _generate_object_id()
        client.batch_tasks(add=[{
            "id": task_id,
            "projectId": test_project,
            "title": "Text Task Test",
            "content": "",
            "kind": "TEXT",
            "status": 0,
            "priority": 0,
            "tags": [],
            "items": [],
            "reminders": [],
            "startDate": None,
            "dueDate": None,
            "isAllDay": False,
            "timeZone": "America/Los_Angeles",
        }])
        task = client.get_task(task_id)
        assert task.get("kind", "TEXT") in ("TEXT", None)


class TestTaskDesc:
    """Tests for --desc field."""

    def test_create_with_description(self, client, test_project):
        """--desc sets the description on a CHECKLIST task."""
        task_id = _generate_object_id()
        client.batch_tasks(add=[{
            "id": task_id,
            "projectId": test_project,
            "title": "Desc Test",
            "desc": "This is a checklist description",
            "kind": "CHECKLIST",
            "content": "",
            "status": 0,
            "priority": 0,
            "tags": [],
            "items": [],
            "reminders": [],
            "startDate": None,
            "dueDate": None,
            "isAllDay": False,
            "timeZone": "America/Los_Angeles",
        }])
        task = client.get_task(task_id)
        assert task.get("desc") == "This is a checklist description"


class TestTaskFloating:
    """Tests for --floating flag."""

    def test_create_floating_task(self, client, test_project):
        """--floating creates a floating (undated) task."""
        task_id = _generate_object_id()
        client.batch_tasks(add=[{
            "id": task_id,
            "projectId": test_project,
            "title": "Floating Test",
            "isFloating": True,
            "content": "",
            "kind": "TEXT",
            "status": 0,
            "priority": 0,
            "tags": [],
            "items": [],
            "reminders": [],
            "startDate": None,
            "dueDate": None,
            "isAllDay": False,
            "timeZone": "America/Los_Angeles",
        }])
        task = client.get_task(task_id)
        assert task.get("isFloating") is True


class TestTaskTimezone:
    """Tests for --tz field."""

    def test_create_with_timezone(self, client, test_project):
        """--tz sets the timezone on a task."""
        task_id = _generate_object_id()
        client.batch_tasks(add=[{
            "id": task_id,
            "projectId": test_project,
            "title": "Timezone Test",
            "timeZone": "America/Chicago",
            "content": "",
            "kind": "TEXT",
            "status": 0,
            "priority": 0,
            "tags": [],
            "items": [],
            "reminders": [],
            "startDate": None,
            "dueDate": None,
            "isAllDay": False,
        }])
        task = client.get_task(task_id)
        assert task.get("timeZone") == "America/Chicago"


class TestTaskProgress:
    """Tests for --progress field."""

    def test_create_with_progress(self, client, test_project):
        """--progress 50 sets progress to 50%."""
        task_id = _generate_object_id()
        client.batch_tasks(add=[{
            "id": task_id,
            "projectId": test_project,
            "title": "Progress Test",
            "progress": 50,
            "content": "",
            "kind": "TEXT",
            "status": 0,
            "priority": 0,
            "tags": [],
            "items": [],
            "reminders": [],
            "startDate": None,
            "dueDate": None,
            "isAllDay": False,
            "timeZone": "America/Los_Angeles",
        }])
        task = client.get_task(task_id)
        assert task.get("progress") == 50


class TestTaskReminders:
    """Tests for --reminder field."""

    def test_create_with_reminder(self, client, test_project):
        """Reminder is wrapped in proper object format."""
        reminder_id = _generate_object_id()
        task_id = _generate_object_id()
        client.batch_tasks(add=[{
            "id": task_id,
            "projectId": test_project,
            "title": "Reminder Test",
            "reminders": [{"id": reminder_id, "trigger": "TRIGGER:-PT30M"}],
            "content": "",
            "kind": "TEXT",
            "status": 0,
            "priority": 0,
            "tags": [],
            "items": [],
            "startDate": None,
            "dueDate": None,
            "isAllDay": False,
            "timeZone": "America/Los_Angeles",
        }])
        task = client.get_task(task_id)
        reminders = task.get("reminders", [])
        assert len(reminders) == 1
        assert reminders[0]["trigger"] == "TRIGGER:-PT30M"


class TestTaskEditFields:
    """Tests for editing new fields."""

    def test_edit_reminder(self, client, test_project):
        """task edit --reminder updates reminders."""
        task_id = _generate_object_id()
        client.batch_tasks(add=[{
            "id": task_id,
            "projectId": test_project,
            "title": "Edit Reminder Test",
            "content": "",
            "kind": "TEXT",
            "status": 0,
            "priority": 0,
            "tags": [],
            "items": [],
            "reminders": [],
            "startDate": None,
            "dueDate": None,
            "isAllDay": False,
            "timeZone": "America/Los_Angeles",
        }])
        reminder_id = _generate_object_id()
        client.batch_tasks(update=[{
            "id": task_id,
            "projectId": test_project,
            "reminders": [{"id": reminder_id, "trigger": "TRIGGER:-PT1H"}],
        }])
        task = client.get_task(task_id)
        reminders = task.get("reminders", [])
        assert len(reminders) == 1
        assert reminders[0]["trigger"] == "TRIGGER:-PT1H"

    def test_edit_all_day(self, client, test_project):
        """task edit --all-day toggles isAllDay."""
        task_id = _generate_object_id()
        client.batch_tasks(add=[{
            "id": task_id,
            "projectId": test_project,
            "title": "Edit AllDay Test",
            "content": "",
            "kind": "TEXT",
            "status": 0,
            "priority": 0,
            "tags": [],
            "items": [],
            "reminders": [],
            "startDate": None,
            "dueDate": None,
            "isAllDay": False,
            "timeZone": "America/Los_Angeles",
        }])
        client.batch_tasks(update=[{
            "id": task_id,
            "projectId": test_project,
            "isAllDay": True,
        }])
        task = client.get_task(task_id)
        assert task.get("isAllDay") is True

    def test_edit_progress(self, client, test_project):
        """task edit --progress updates progress."""
        task_id = _generate_object_id()
        client.batch_tasks(add=[{
            "id": task_id,
            "projectId": test_project,
            "title": "Edit Progress Test",
            "content": "",
            "kind": "TEXT",
            "status": 0,
            "priority": 0,
            "tags": [],
            "items": [],
            "reminders": [],
            "startDate": None,
            "dueDate": None,
            "isAllDay": False,
            "timeZone": "America/Los_Angeles",
        }])
        client.batch_tasks(update=[{
            "id": task_id,
            "projectId": test_project,
            "progress": 75,
        }])
        task = client.get_task(task_id)
        assert task.get("progress") == 75

    def test_edit_repeat_from(self, client, test_project):
        """task edit --repeat-from 1 sets repeatFrom."""
        task_id = _generate_object_id()
        client.batch_tasks(add=[{
            "id": task_id,
            "projectId": test_project,
            "title": "Edit RepeatFrom Test",
            "content": "",
            "kind": "TEXT",
            "status": 0,
            "priority": 0,
            "tags": [],
            "items": [],
            "reminders": [],
            "startDate": None,
            "dueDate": "2026-06-01T00:00:00+0000",
            "isAllDay": False,
            "timeZone": "America/Los_Angeles",
            "repeatFlag": "RRULE:FREQ=WEEKLY;INTERVAL=1",
        }])
        client.batch_tasks(update=[{
            "id": task_id,
            "projectId": test_project,
            "repeatFrom": "1",
        }])
        task = client.get_task(task_id)
        assert task.get("repeatFrom") == "1"

    def test_create_with_ex_date(self, client, test_project):
        """--ex-date on recurring task."""
        task_id = _generate_object_id()
        client.batch_tasks(add=[{
            "id": task_id,
            "projectId": test_project,
            "title": "ExDate Test",
            "content": "",
            "kind": "TEXT",
            "status": 0,
            "priority": 0,
            "tags": [],
            "items": [],
            "reminders": [],
            "startDate": None,
            "dueDate": "2026-06-01T00:00:00+0000",
            "isAllDay": False,
            "timeZone": "America/Los_Angeles",
            "repeatFlag": "RRULE:FREQ=WEEKLY;INTERVAL=1",
            "exDate": ["2026-06-08"],
        }])
        task = client.get_task(task_id)
        assert "2026-06-08" in (task.get("exDate") or [])

    def test_edit_repeat_first_date(self, client, test_project):
        """task edit --repeat-first sets repeatFirstDate."""
        task_id = _generate_object_id()
        client.batch_tasks(add=[{
            "id": task_id,
            "projectId": test_project,
            "title": "RepeatFirst Test",
            "content": "",
            "kind": "TEXT",
            "status": 0,
            "priority": 0,
            "tags": [],
            "items": [],
            "reminders": [],
            "startDate": None,
            "dueDate": "2026-06-01T00:00:00+0000",
            "isAllDay": False,
            "timeZone": "America/Los_Angeles",
            "repeatFlag": "RRULE:FREQ=WEEKLY;INTERVAL=1",
        }])
        client.batch_tasks(update=[{
            "id": task_id,
            "projectId": test_project,
            "repeatFirstDate": "2026-05-25",
        }])
        task = client.get_task(task_id)
        assert task.get("repeatFirstDate") == "2026-05-25"


class TestCommentEdit:
    """Tests for comment edit command."""

    def test_comment_edit(self, client, test_project):
        """Edit a comment's text."""
        task_id = _generate_object_id()
        client.batch_tasks(add=[{
            "id": task_id,
            "projectId": test_project,
            "title": "Comment Edit Test",
            "content": "",
            "kind": "TEXT",
            "status": 0,
            "priority": 0,
            "tags": [],
            "items": [],
            "reminders": [],
            "startDate": None,
            "dueDate": None,
            "isAllDay": False,
            "timeZone": "America/Los_Angeles",
        }])
        # Create a comment
        result = client.create_task_comment(test_project, task_id, "Original text")
        comment_id = result.get("id") if isinstance(result, dict) else None
        if not comment_id:
            # Try to get it from list
            comments = client.get_task_comments(test_project, task_id)
            if comments:
                comment_id = comments[0].get("id")
        assert comment_id, "Failed to create comment"
        # Edit it
        client.edit_task_comment(test_project, task_id, comment_id, "Updated text")
        # Verify
        comments = client.get_task_comments(test_project, task_id)
        found = next((c for c in comments if c.get("id") == comment_id), None)
        assert found is not None, "Comment not found after edit"
