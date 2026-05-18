"""Task commands — full CRUD, search, batch operations."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

import click

from ticktick_cli.api.v2 import _generate_object_id
from ticktick_cli.auth import get_client
from ticktick_cli.dates import parse_date
from ticktick_cli.models.comment import Activity, Comment
from ticktick_cli.output import (
    is_dry_run,
    output_dry_run,
    output_error,
    output_existing_item,
    output_item,
    output_list,
    output_message,
)

PRIORITY_MAP = {"none": 0, "low": 1, "medium": 3, "high": 5}
PRIORITY_REVERSE = {0: "none", 1: "low", 3: "medium", 5: "high"}
_FETCH_ALL_LIMIT = 10_000


def _format_task(task: dict[str, Any]) -> dict[str, Any]:
    """Normalize task dict for output."""
    # Delegate to Pydantic model when available for consistency
    from ticktick_cli.models.task import Task
    try:
        return Task(**task).to_output()
    except Exception:
        pass
    return {
        "id": task.get("id", ""),
        "title": task.get("title", ""),
        "status": "completed" if task.get("status", 0) >= 2 else "active",
        "priority": PRIORITY_REVERSE.get(task.get("priority", 0), "none"),
        "projectId": task.get("projectId", ""),
        "dueDate": task.get("dueDate", ""),
        "startDate": task.get("startDate", ""),
        "tags": task.get("tags", []),
        "content": task.get("content", ""),
        "isAllDay": task.get("isAllDay", False),
        "parentId": task.get("parentId"),
        "columnId": task.get("columnId"),
        "pinnedTime": task.get("pinnedTime"),
        "items": task.get("items", []),
        "kind": task.get("kind", ""),
        "assignee": task.get("assignee"),
        "desc": task.get("desc", ""),
        "isFloating": task.get("isFloating"),
        "timeZone": task.get("timeZone", ""),
        "progress": task.get("progress"),
        "sortOrder": task.get("sortOrder"),
        "repeatFrom": task.get("repeatFrom", ""),
        "repeatFlag": task.get("repeatFlag", ""),
        "exDate": task.get("exDate", []),
        "repeatFirstDate": task.get("repeatFirstDate", ""),
        "commentCount": task.get("commentCount"),
        "reminders": task.get("reminders", []),
    }


V2_ONLY_FIELDS = frozenset({
    "assignee", "kind", "desc", "isFloating", "timeZone",
    "progress", "sortOrder", "repeatFrom", "exDate",
    "repeatFirstDate", "reminders",
})


def _require_v2_for_fields(ctx: click.Context, client: Any, **fields: Any) -> None:
    """Check if any V2-only fields are used without V2 auth."""
    if client.has_v2:
        return
    used_v2 = [k for k, v in fields.items() if v and k in V2_ONLY_FIELDS]
    if used_v2:
        output_error(
            f"Fields require V2 authentication: {', '.join(sorted(used_v2))}. "
            f"Run: ticktick auth login-v2 --username <email>",
            ctx,
        )
        raise SystemExit(1) from None


def _request_page_limit(ctx: click.Context, limit: int) -> int:
    """Fetch enough rows for global offset pagination before local slicing."""
    offset = int(ctx.obj.get("offset", 0)) if ctx.obj else 0
    fetch_all = bool(ctx.obj.get("all")) if ctx.obj else False
    if fetch_all:
        return max(limit + offset, _FETCH_ALL_LIMIT)
    return limit + offset


@click.group("task")
def task_group() -> None:
    """Manage tasks."""


@task_group.command("add")
@click.argument("title")
@click.option("--project", "-p", default=None, help="Project name or ID")
@click.option("--content", "-c", default=None, help="Task body/notes")
@click.option(
    "--priority",
    type=click.Choice(["none", "low", "medium", "high"]),
    default="none",
    help="Task priority",
)
@click.option("--due", "-d", default=None, help="Due date (YYYY-MM-DD, today, tomorrow, monday, +3d, +1w, +2m)")
@click.option("--start", default=None, help="Start date")
@click.option("--tag", "-t", multiple=True, help="Tags (repeatable)")
@click.option("--all-day", is_flag=True, help="Mark as all-day task")
@click.option("--repeat", default=None, help="Recurrence RRULE (e.g., RRULE:FREQ=DAILY)")
@click.option("--reminder", multiple=True, help="Reminder triggers (e.g., TRIGGER:-PT30M)")
@click.option("--assignee", type=int, default=None, help="Assignee user ID (V2 only, shared project required)")
@click.option("--kind", type=click.Choice(["TEXT", "CHECKLIST"]), default=None, help="Task type (V2 only)")
@click.option("--desc", default=None, help="Description (for CHECKLIST tasks, V2 only)")
@click.option("--floating", is_flag=True, default=None, help="Floating task — no fixed date (V2 only)")
@click.option("--tz", "time_zone", default=None, help="IANA timezone (e.g., America/Los_Angeles, V2 only)")
@click.option("--progress", type=int, default=None, help="Progress 0-100 (V2 only)")
@click.option("--sort-order", type=int, default=None, help="Manual sort position (V2 only)")
@click.option("--repeat-from", type=click.Choice(["0", "1", "2"]), default=None, help="Repeat origin: 0=due, 1=completion, 2=both (V2 only)")
@click.option("--ex-date", multiple=True, default=None, help="Excluded dates for recurring tasks, YYYY-MM-DD (repeatable, V2 only)")
@click.option("--repeat-first", default=None, help="First occurrence date YYYY-MM-DD for recurring task (V2 only)")
@click.option("--column", default=None, help="Kanban column ID (V2 only)")
@click.option("--if-not-exists", "if_not_exists", is_flag=True, help="Skip creation if a task with the same title exists in the project")
@click.pass_context
def task_add(
    ctx: click.Context,
    title: str,
    project: str | None,
    content: str | None,
    priority: str,
    due: str | None,
    start: str | None,
    tag: tuple[str, ...],
    all_day: bool,
    repeat: str | None,
    reminder: tuple[str, ...],
    assignee: int | None,
    kind: str | None,
    desc: str | None,
    floating: bool | None,
    time_zone: str | None,
    progress: int | None,
    sort_order: int | None,
    repeat_from: str | None,
    ex_date: tuple[str, ...] | None,
    repeat_first: str | None,
    column: str | None,
    if_not_exists: bool,
) -> None:
    """Create a new task."""
    task_data: dict[str, Any] = {"title": title}
    if project:
        task_data["project"] = project
    if content:
        task_data["content"] = content
    task_data["priority"] = PRIORITY_MAP[priority]
    if due:
        task_data["dueDate"] = parse_date(due)
    if start:
        task_data["startDate"] = parse_date(start)
    if tag:
        task_data["tags"] = list(tag)
    if all_day:
        task_data["isAllDay"] = True
    if repeat:
        task_data["repeatFlag"] = repeat
    if reminder:
        # Wrap raw strings into proper reminder objects for V2 API
        from ticktick_cli.api.v2 import _generate_object_id
        task_data["reminders"] = [
            {"id": _generate_object_id(), "trigger": r} for r in reminder
        ]
    if assignee is not None:
        task_data["assignee"] = assignee
    if kind:
        task_data["kind"] = kind
    if desc:
        task_data["desc"] = desc
    if floating is not None:
        task_data["isFloating"] = floating
    if time_zone:
        task_data["timeZone"] = time_zone
    if progress is not None:
        task_data["progress"] = progress
    if sort_order is not None:
        task_data["sortOrder"] = sort_order
    if repeat_from:
        task_data["repeatFrom"] = repeat_from
    if ex_date:
        task_data["exDate"] = list(ex_date)
    if repeat_first:
        task_data["repeatFirstDate"] = repeat_first
    if column:
        task_data["columnId"] = column

    if is_dry_run(ctx):
        output_dry_run("task.add", task_data, ctx)
        return

    client = get_client(ctx.obj.get("profile", "default"))

    _require_v2_for_fields(
        ctx, client,
        assignee=task_data.get("assignee"),
        kind=task_data.get("kind"),
        desc=task_data.get("desc"),
        isFloating=task_data.get("isFloating"),
        timeZone=task_data.get("timeZone"),
        progress=task_data.get("progress"),
        sortOrder=task_data.get("sortOrder"),
        repeatFrom=task_data.get("repeatFrom"),
        exDate=task_data.get("exDate"),
        repeatFirstDate=task_data.get("repeatFirstDate"),
    )

    if if_not_exists:
        try:
            tasks = client.get_all_tasks()
            project_id = _resolve_project_id(client, project) if project else None
            for t in tasks:
                if (
                    t.get("title", "").lower() == title.lower()
                    and t.get("status", 0) < 2
                    and (project_id is None or t.get("projectId") == project_id)
                ):
                    output_existing_item(_format_task(t), ctx)
                    return
        except Exception as e:
            output_error(str(e), ctx)
            raise SystemExit(1) from None

    if project:
        task_data["projectId"] = _resolve_project_id(client, project)
        task_data.pop("project", None)

    try:
        if client.has_v2:
            result = client.v2.batch_tasks(add=[task_data])
            output_message(f"Task created: {title}", ctx)
        else:
            result = client.v1.create_task(task_data)
            output_item(_format_task(result), ctx)
    except Exception as e:
        output_error(str(e), ctx)
        raise SystemExit(1) from None


@task_group.command("list")
@click.option("--project", "-p", default=None, help="Filter by project name or ID")
@click.option(
    "--status",
    type=click.Choice(["uncompleted", "completed", "abandoned", "all"]),
    default="uncompleted",
)
@click.option("--priority", type=click.Choice(["none", "low", "medium", "high"]), default=None)
@click.option("--due", default=None, help="Filter: today, overdue, this-week, YYYY-MM-DD")
@click.option("--tag", "-t", multiple=True, help="Filter by tag")
@click.option("--sort", type=click.Choice(["due", "priority", "title", "created"]), default="due")
@click.option("--limit", "-n", type=int, default=50, help="Max results")
@click.pass_context
def task_list(
    ctx: click.Context,
    project: str | None,
    status: str,
    priority: str | None,
    due: str | None,
    tag: tuple[str, ...],
    sort: str,
    limit: int,
) -> None:
    """List tasks with optional filters."""
    client = get_client(ctx.obj.get("profile", "default"))

    try:
        if status == "completed" and client.has_v2:
            now = datetime.now()
            tasks = client.v2.get_completed_tasks(now - timedelta(days=365), now, limit=limit)
        elif client.has_v2:
            tasks = client.get_all_tasks()
        else:
            # V1: need to list per project
            projects = client.v1.list_projects()
            tasks = []
            for proj in projects:
                data = client.v1.get_project_with_data(proj["id"])
                tasks.extend(data.get("tasks", []))

        # Apply filters
        if project:
            pid = _resolve_project_id(client, project)
            tasks = [t for t in tasks if t.get("projectId") == pid]
        if status == "uncompleted":
            tasks = [t for t in tasks if t.get("status", 0) == 0]
        elif status == "abandoned":
            tasks = [t for t in tasks if t.get("status", 0) == -1]
        if priority:
            p = PRIORITY_MAP[priority]
            tasks = [t for t in tasks if t.get("priority", 0) == p]
        if tag:
            tag_set = set(tag)
            tasks = [t for t in tasks if tag_set.intersection(set(t.get("tags", [])))]
        if due:
            tasks = _filter_by_due(tasks, due)

        # Sort
        tasks = _sort_tasks(tasks, sort)

        formatted = [_format_task(t) for t in tasks]
        columns = ["id", "title", "priority", "dueDate", "projectId", "tags"]
        output_list(formatted, columns=columns, title="Tasks", ctx=ctx, limit=limit)
    except Exception as e:
        output_error(str(e), ctx)
        raise SystemExit(1) from None


@task_group.command("show")
@click.argument("task_id")
@click.pass_context
def task_show(ctx: click.Context, task_id: str) -> None:
    """Show detailed task information."""
    client = get_client(ctx.obj.get("profile", "default"))
    try:
        if client.has_v2:
            task = client.v2.get_task(task_id)
        else:
            # V1 requires project_id — search for it
            task = _find_task_v1(client, task_id)
        output_item(_format_task(task), ctx)
    except Exception as e:
        output_error(str(e), ctx)
        raise SystemExit(1) from None


@task_group.command("edit")
@click.argument("task_id")
@click.option("--title", default=None)
@click.option("--content", default=None)
@click.option("--priority", type=click.Choice(["none", "low", "medium", "high"]), default=None)
@click.option("--due", default=None)
@click.option("--start", default=None)
@click.option("--project", default=None)
@click.option("--tag", "-t", multiple=True)
@click.option("--repeat", default=None)
@click.option("--column", default=None, help="Kanban column ID")
@click.option("--all-day", is_flag=True, default=None, help="Mark as all-day task")
@click.option("--reminder", "reminders_opt", multiple=True, help="Reminder triggers (e.g., TRIGGER:-PT30M). Replaces existing reminders.")
@click.option("--assignee", type=int, default=None, help="Assignee user ID (V2 only)")
@click.option("--kind", type=click.Choice(["TEXT", "CHECKLIST"]), default=None, help="Task type (V2 only)")
@click.option("--desc", default=None, help="Description (V2 only)")
@click.option("--floating", "floating_opt", is_flag=True, default=None, help="Floating task (V2 only)")
@click.option("--tz", "time_zone_opt", default=None, help="IANA timezone (V2 only)")
@click.option("--progress", type=int, default=None, help="Progress 0-100 (V2 only)")
@click.option("--sort-order", type=int, default=None, help="Manual sort position (V2 only)")
@click.option("--repeat-from", type=click.Choice(["0", "1", "2"]), default=None, help="Repeat origin (V2 only)")
@click.option("--ex-date", "ex_date_opt", multiple=True, default=None, help="Excluded dates YYYY-MM-DD (repeatable, V2 only)")
@click.option("--repeat-first", default=None, help="First occurrence date YYYY-MM-DD (V2 only)")
@click.pass_context
def task_edit(
    ctx: click.Context,
    task_id: str,
    title: str | None = None,
    content: str | None = None,
    priority: str | None = None,
    due: str | None = None,
    start: str | None = None,
    project: str | None = None,
    tag: tuple[str, ...] | None = None,
    repeat: str | None = None,
    column: str | None = None,
    all_day: bool | None = None,
    reminders_opt: tuple[str, ...] | None = None,
    assignee: int | None = None,
    kind: str | None = None,
    desc: str | None = None,
    floating_opt: bool | None = None,
    time_zone_opt: str | None = None,
    progress: int | None = None,
    sort_order: int | None = None,
    repeat_from: str | None = None,
    ex_date_opt: tuple[str, ...] | None = None,
    repeat_first: str | None = None,
) -> None:
    """Edit a task's properties."""
    update: dict[str, Any] = {"id": task_id}
    if title:
        update["title"] = title
    if content:
        update["content"] = content
    if priority:
        update["priority"] = PRIORITY_MAP[priority]
    if due:
        update["dueDate"] = parse_date(due)
    if start:
        update["startDate"] = parse_date(start)
    if tag:
        update["tags"] = list(tag)
    if repeat:
        update["repeatFlag"] = repeat
    if column:
        update["columnId"] = column
    if all_day is not None:
        update["isAllDay"] = all_day
    if reminders_opt:
        from ticktick_cli.api.v2 import _generate_object_id
        update["reminders"] = [
            {"id": _generate_object_id(), "trigger": r} for r in reminders_opt
        ]
    if assignee is not None:
        update["assignee"] = assignee
    if kind:
        update["kind"] = kind
    if desc:
        update["desc"] = desc
    if floating_opt is not None:
        update["isFloating"] = floating_opt
    if time_zone_opt:
        update["timeZone"] = time_zone_opt
    if progress is not None:
        update["progress"] = progress
    if sort_order is not None:
        update["sortOrder"] = sort_order
    if repeat_from:
        update["repeatFrom"] = repeat_from
    if ex_date_opt:
        update["exDate"] = list(ex_date_opt)
    if repeat_first:
        update["repeatFirstDate"] = repeat_first

    if is_dry_run(ctx):
        output_dry_run("task.edit", update, ctx)
        return

    client = get_client(ctx.obj.get("profile", "default"))

    _require_v2_for_fields(
        ctx, client,
        assignee=update.get("assignee"),
        kind=update.get("kind"),
        desc=update.get("desc"),
        isFloating=update.get("isFloating"),
        timeZone=update.get("timeZone"),
        progress=update.get("progress"),
        sortOrder=update.get("sortOrder"),
        repeatFrom=update.get("repeatFrom"),
        exDate=update.get("exDate"),
        repeatFirstDate=update.get("repeatFirstDate"),
    )

    if project:
        update["projectId"] = _resolve_project_id(client, project)
    try:
        if client.has_v2:
            # Need projectId for V2 update
            if "projectId" not in update:
                task = client.v2.get_task(task_id)
                update["projectId"] = task.get("projectId", "")
            client.v2.batch_tasks(update=[update])
        else:
            client.v1.update_task(task_id, update)
        output_message(f"Task {task_id} updated.", ctx)
    except Exception as e:
        output_error(str(e), ctx)
        raise SystemExit(1) from None


@task_group.command("done")
@click.argument("task_ids", nargs=-1, required=True)
@click.pass_context
def task_done(ctx: click.Context, task_ids: tuple[str, ...]) -> None:
    """Mark task(s) as completed."""
    if is_dry_run(ctx):
        output_dry_run("task.done", {"task_ids": list(task_ids)}, ctx)
        return

    client = get_client(ctx.obj.get("profile", "default"))
    try:
        if client.has_v1:
            for tid in task_ids:
                task = _get_task_any(client, tid)
                client.v1.complete_task(task["projectId"], tid)
        elif client.has_v2:
            updates = []
            for tid in task_ids:
                task = client.v2.get_task(tid)
                updates.append({"id": tid, "projectId": task["projectId"], "status": 2})
            client.v2.batch_tasks(update=updates)
        output_message(f"Completed {len(task_ids)} task(s).", ctx)
    except Exception as e:
        output_error(str(e), ctx)
        raise SystemExit(1) from None


@task_group.command("abandon")
@click.argument("task_ids", nargs=-1, required=True)
@click.pass_context
def task_abandon(ctx: click.Context, task_ids: tuple[str, ...]) -> None:
    """Mark task(s) as 'won't do' (V2 only)."""
    client = get_client(ctx.obj.get("profile", "default"))
    try:
        updates = []
        for tid in task_ids:
            task = client.v2.get_task(tid)
            updates.append({"id": tid, "projectId": task["projectId"], "status": -1})
        client.v2.batch_tasks(update=updates)
        output_message(f"Abandoned {len(task_ids)} task(s).", ctx)
    except Exception as e:
        output_error(str(e), ctx)
        raise SystemExit(1) from None


@task_group.command("delete")
@click.argument("task_ids", nargs=-1, required=True)
@click.option("--yes", is_flag=True, help="Skip confirmation")
@click.pass_context
def task_delete(ctx: click.Context, task_ids: tuple[str, ...], yes: bool) -> None:
    """Delete task(s)."""
    if is_dry_run(ctx):
        output_dry_run("task.delete", {"task_ids": list(task_ids)}, ctx)
        return

    if not yes:
        click.confirm(f"Delete {len(task_ids)} task(s)?", abort=True)
    client = get_client(ctx.obj.get("profile", "default"))
    try:
        if client.has_v2:
            deletes = []
            for tid in task_ids:
                task = client.v2.get_task(tid)
                deletes.append({"taskId": tid, "projectId": task["projectId"]})
            client.v2.batch_tasks(delete=deletes)
        else:
            for tid in task_ids:
                task = _find_task_v1(client, tid)
                client.v1.delete_task(task["projectId"], tid)
        output_message(f"Deleted {len(task_ids)} task(s).", ctx)
    except Exception as e:
        output_error(str(e), ctx)
        raise SystemExit(1) from None


@task_group.command("move")
@click.argument("task_id")
@click.option("--project", "-p", required=True, help="Target project name or ID")
@click.pass_context
def task_move(ctx: click.Context, task_id: str, project: str) -> None:
    """Move a task to a different project (V2)."""
    client = get_client(ctx.obj.get("profile", "default"))
    try:
        task = client.v2.get_task(task_id)
        to_project = _resolve_project_id(client, project)
        client.v2.move_tasks([{
            "taskId": task_id,
            "fromProjectId": task["projectId"],
            "toProjectId": to_project,
        }])
        output_message(f"Task {task_id} moved to {project}.", ctx)
    except Exception as e:
        output_error(str(e), ctx)
        raise SystemExit(1) from None


@task_group.command("search")
@click.argument("query")
@click.option("--limit", "-n", type=int, default=20)
@click.option("--project", "-p", default=None, help="Filter by project name or ID")
@click.option("--tag", "-t", multiple=True, help="Filter by tag")
@click.option("--status", type=click.Choice(["active", "completed", "abandoned", "all"]), default="all", help="Filter by status")
@click.option("--priority", type=click.Choice(["none", "low", "medium", "high"]), default=None, help="Filter by priority")
@click.pass_context
def task_search(
    ctx: click.Context,
    query: str,
    limit: int,
    project: str | None,
    tag: tuple[str, ...],
    status: str,
    priority: str | None,
) -> None:
    """Search tasks by text with optional filters."""
    client = get_client(ctx.obj.get("profile", "default"))
    try:
        tasks = client.get_all_tasks()
        q = query.lower()
        matches = [
            t
            for t in tasks
            if q in t.get("title", "").lower() or q in t.get("content", "").lower()
        ]
        # Apply additional filters
        if project:
            pid = _resolve_project_id(client, project)
            matches = [t for t in matches if t.get("projectId") == pid]
        if status == "active":
            matches = [t for t in matches if t.get("status", 0) == 0]
        elif status == "completed":
            matches = [t for t in matches if t.get("status", 0) >= 2]
        elif status == "abandoned":
            matches = [t for t in matches if t.get("status", 0) == -1]
        if priority:
            p_val = PRIORITY_MAP[priority]
            matches = [t for t in matches if t.get("priority", 0) == p_val]
        if tag:
            tag_set = set(tag)
            matches = [t for t in matches if tag_set.intersection(set(t.get("tags", [])))]
        formatted = [_format_task(t) for t in matches]
        output_list(
            formatted,
            columns=["id", "title", "priority", "dueDate", "projectId"],
            ctx=ctx,
            limit=limit,
        )
    except Exception as e:
        output_error(str(e), ctx)
        raise SystemExit(1) from None


@task_group.command("today")
@click.pass_context
def task_today(ctx: click.Context) -> None:
    """List tasks due today."""
    ctx.invoke(task_list, due="today")


@task_group.command("overdue")
@click.pass_context
def task_overdue(ctx: click.Context) -> None:
    """List overdue tasks."""
    ctx.invoke(task_list, due="overdue")


@task_group.command("completed")
@click.option("--from", "from_date", default=None, help="Start date (YYYY-MM-DD)")
@click.option("--to", "to_date", default=None, help="End date (YYYY-MM-DD)")
@click.option("--limit", "-n", type=int, default=50)
@click.pass_context
def task_completed(ctx: click.Context, from_date: str | None, to_date: str | None, limit: int) -> None:
    """List completed tasks (V2)."""
    client = get_client(ctx.obj.get("profile", "default"))
    try:
        now = datetime.now()
        fd = datetime.fromisoformat(from_date) if from_date else now - timedelta(days=30)
        td = datetime.fromisoformat(to_date) if to_date else now
        tasks = client.v2.get_completed_tasks(fd, td, limit=_request_page_limit(ctx, limit))
        formatted = [_format_task(t) for t in tasks]
        output_list(
            formatted,
            columns=["id", "title", "priority", "dueDate"],
            title="Completed Tasks",
            ctx=ctx,
            limit=limit,
        )
    except Exception as e:
        output_error(str(e), ctx)
        raise SystemExit(1) from None


@task_group.command("trash")
@click.option("--limit", "-n", type=int, default=50)
@click.pass_context
def task_trash(ctx: click.Context, limit: int) -> None:
    """List deleted tasks in trash (V2)."""
    client = get_client(ctx.obj.get("profile", "default"))
    try:
        result = client.v2.get_deleted_tasks(limit=_request_page_limit(ctx, limit))
        tasks = result.get("tasks", []) if isinstance(result, dict) else result
        formatted = [_format_task(t) for t in tasks]
        output_list(
            formatted,
            columns=["id", "title", "priority"],
            title="Trash",
            ctx=ctx,
            limit=limit,
        )
    except Exception as e:
        output_error(str(e), ctx)
        raise SystemExit(1) from None


@task_group.command("pin")
@click.argument("task_id")
@click.pass_context
def task_pin(ctx: click.Context, task_id: str) -> None:
    """Pin a task (V2)."""
    client = get_client(ctx.obj.get("profile", "default"))
    try:
        task = client.v2.get_task(task_id)
        now = datetime.now().strftime("%Y-%m-%dT%H:%M:%S.000+0000")
        client.v2.batch_tasks(update=[{
            "id": task_id,
            "projectId": task["projectId"],
            "pinnedTime": now,
        }])
        output_message(f"Task {task_id} pinned.", ctx)
    except Exception as e:
        output_error(str(e), ctx)
        raise SystemExit(1) from None


@task_group.command("unpin")
@click.argument("task_id")
@click.pass_context
def task_unpin(ctx: click.Context, task_id: str) -> None:
    """Unpin a task (V2)."""
    client = get_client(ctx.obj.get("profile", "default"))
    try:
        task = client.v2.get_task(task_id)
        client.v2.batch_tasks(update=[{
            "id": task_id,
            "projectId": task["projectId"],
            "pinnedTime": None,
        }])
        output_message(f"Task {task_id} unpinned.", ctx)
    except Exception as e:
        output_error(str(e), ctx)
        raise SystemExit(1) from None


@task_group.command("batch-add")
@click.option("--file", "-f", "filepath", required=True, type=click.Path(exists=True), help="JSON file with task list")
@click.pass_context
def task_batch_add(ctx: click.Context, filepath: str) -> None:
    """Bulk create tasks from a JSON file."""
    import json

    client = get_client(ctx.obj.get("profile", "default"))
    try:
        with open(filepath) as f:
            tasks = json.load(f)
        if not isinstance(tasks, list):
            tasks = [tasks]
        client.v2.batch_tasks(add=tasks)
        output_message(f"Created {len(tasks)} task(s) from {filepath}.", ctx)
    except Exception as e:
        output_error(str(e), ctx)
        raise SystemExit(1) from None


# ── Comment subgroup ──────────────────────────────────────────


@task_group.group("comment")
def comment_group() -> None:
    """Manage task comments."""


@comment_group.command("list")
@click.argument("task_id")
@click.option("--project", "project_id", default=None, help="Project ID (auto-detected if omitted)")
@click.pass_context
def comment_list(ctx: click.Context, task_id: str, project_id: str | None) -> None:
    """List comments on a task."""
    client = get_client(ctx.obj.get("profile", "default"))
    try:
        if not project_id:
            task = client.v2.get_task(task_id)
            project_id = task.get("projectId", "")
        raw = client.v2.get_task_comments(project_id, task_id)
        comments = [Comment(**c).to_output() for c in raw]
        output_list(comments, columns=["id", "title", "createdTime"], title="Comments", ctx=ctx)
    except Exception as e:
        output_error(str(e), ctx)
        raise SystemExit(1) from None


@comment_group.command("add")
@click.argument("task_id")
@click.argument("text")
@click.option("--project", "project_id", default=None, help="Project ID (auto-detected if omitted)")
@click.pass_context
def comment_add(ctx: click.Context, task_id: str, text: str, project_id: str | None) -> None:
    """Add a comment to a task."""
    if is_dry_run(ctx):
        output_dry_run("task.comment.add", {"task_id": task_id, "text": text}, ctx)
        return
    client = get_client(ctx.obj.get("profile", "default"))
    try:
        if not project_id:
            task = client.v2.get_task(task_id)
            project_id = task.get("projectId", "")
        client.v2.create_task_comment(project_id, task_id, text)
        output_message("Comment added.", ctx)
    except Exception as e:
        output_error(str(e), ctx)
        raise SystemExit(1) from None


@comment_group.command("delete")
@click.argument("task_id")
@click.argument("comment_id")
@click.option("--project", "project_id", default=None, help="Project ID (auto-detected if omitted)")
@click.pass_context
def comment_delete(ctx: click.Context, task_id: str, comment_id: str, project_id: str | None) -> None:
    """Delete a comment from a task."""
    if is_dry_run(ctx):
        output_dry_run("task.comment.delete", {"comment_id": comment_id}, ctx)
        return
    client = get_client(ctx.obj.get("profile", "default"))
    try:
        if not project_id:
            task = client.v2.get_task(task_id)
            project_id = task.get("projectId", "")
        client.v2.delete_task_comment(project_id, task_id, comment_id)
        output_message("Comment deleted.", ctx)
    except Exception as e:
        output_error(str(e), ctx)
        raise SystemExit(1) from None


@comment_group.command("edit")
@click.argument("task_id")
@click.argument("comment_id")
@click.argument("text")
@click.option("--project", "project_id", default=None, help="Project ID (auto-detected if omitted)")
@click.pass_context
def comment_edit(ctx: click.Context, task_id: str, comment_id: str, text: str, project_id: str | None) -> None:
    """Edit a comment's text."""
    if is_dry_run(ctx):
        output_dry_run("task.comment.edit", {"comment_id": comment_id, "text": text}, ctx)
        return
    client = get_client(ctx.obj.get("profile", "default"))
    try:
        if not project_id:
            task = client.v2.get_task(task_id)
            project_id = task.get("projectId", "")
        client.v2.edit_task_comment(project_id, task_id, comment_id, text)
        output_message("Comment updated.", ctx)
    except Exception as e:
        output_error(str(e), ctx)
        raise SystemExit(1) from None


# ── Activity command ──────────────────────────────────────────


@task_group.command("activity")
@click.argument("task_id")
@click.pass_context
def task_activity(ctx: click.Context, task_id: str) -> None:
    """Show change history for a task."""
    client = get_client(ctx.obj.get("profile", "default"))
    try:
        raw = client.v2.get_task_activities(task_id)
        activities = [Activity(**a).to_output() for a in raw]
        output_list(activities, columns=["id", "action", "when"], title="Activities", ctx=ctx)
    except Exception as e:
        output_error(str(e), ctx)
        raise SystemExit(1) from None


# ── Duplicate command ─────────────────────────────────────────


@task_group.command("duplicate")
@click.argument("task_id")
@click.pass_context
def task_duplicate(ctx: click.Context, task_id: str) -> None:
    """Duplicate a task."""
    if is_dry_run(ctx):
        output_dry_run("task.duplicate", {"task_id": task_id}, ctx)
        return
    client = get_client(ctx.obj.get("profile", "default"))
    try:
        task = client.v2.get_task(task_id)
        new_task = dict(task)
        new_task["id"] = _generate_object_id()
        new_task["title"] = task.get("title", "") + " (copy)"
        # Remove server-generated fields
        for key in ("etag", "sortOrder", "modifiedTime", "createdTime"):
            new_task.pop(key, None)
        client.v2.batch_tasks(add=[new_task])
        output_message(f"Task duplicated. New ID: {new_task['id']}", ctx)
    except Exception as e:
        output_error(str(e), ctx)
        raise SystemExit(1) from None


# ── Convert (task ↔ note) ─────────────────────────────────────


@task_group.command("convert")
@click.argument("task_id")
@click.option(
    "--to",
    "target_kind",
    required=True,
    type=click.Choice(["note", "task"]),
    help="Convert to 'note' or back to 'task'",
)
@click.pass_context
def task_convert(ctx: click.Context, task_id: str, target_kind: str) -> None:
    """Convert a task to a note or a note back to a task."""
    kind_value = "NOTE" if target_kind == "note" else "TEXT"

    if is_dry_run(ctx):
        output_dry_run("task.convert", {"task_id": task_id, "kind": kind_value}, ctx)
        return

    client = get_client(ctx.obj.get("profile", "default"))
    try:
        task = client.v2.get_task(task_id)
        client.v2.batch_tasks(update=[{
            "id": task_id,
            "projectId": task.get("projectId", ""),
            "kind": kind_value,
        }])
        output_message(f"Task {task_id} converted to {target_kind}.", ctx)
    except Exception as e:
        output_error(str(e), ctx)
        raise SystemExit(1) from None


# ── Helpers ───────────────────────────────────────────────────


def _resolve_project_id(client: Any, name_or_id: str) -> str:
    """Resolve project name to ID. If it looks like an ID, return as-is."""
    if len(name_or_id) == 24 and name_or_id.isalnum():
        return name_or_id  # Likely a MongoDB-style ID
    projects = client.list_projects() if hasattr(client, "list_projects") else []
    for proj in projects:
        if proj.get("name", "").lower() == name_or_id.lower():
            return proj["id"]
    return name_or_id  # Fallback: treat as ID



def _filter_by_due(tasks: list[dict], due_filter: str) -> list[dict]:
    """Filter tasks by due date."""
    now = datetime.now()
    today_str = now.strftime("%Y-%m-%d")

    def get_due(t: dict) -> str | None:
        d = t.get("dueDate", "")
        return d[:10] if d else None

    if due_filter == "today":
        return [t for t in tasks if get_due(t) == today_str]
    elif due_filter == "overdue":
        return [t for t in tasks if get_due(t) and get_due(t) < today_str]
    elif due_filter == "this-week":
        week_end = (now + timedelta(days=7)).strftime("%Y-%m-%d")
        return [t for t in tasks if get_due(t) and today_str <= get_due(t) <= week_end]
    else:
        return [t for t in tasks if get_due(t) == due_filter]


def _sort_tasks(tasks: list[dict], sort_key: str) -> list[dict]:
    """Sort tasks by given key."""
    key_map = {
        "due": lambda t: t.get("dueDate") or "9999",
        "priority": lambda t: -t.get("priority", 0),
        "title": lambda t: t.get("title", "").lower(),
        "created": lambda t: t.get("createdTime") or "",
    }
    return sorted(tasks, key=key_map.get(sort_key, key_map["due"]))


def _get_task_any(client: Any, task_id: str) -> dict:
    """Get task from either V2 or V1."""
    if client.has_v2:
        return client.v2.get_task(task_id)
    return _find_task_v1(client, task_id)


def _find_task_v1(client: Any, task_id: str) -> dict:
    """Find task via V1 (requires searching across projects)."""
    projects = client.v1.list_projects()
    for proj in projects:
        try:
            return client.v1.get_task(proj["id"], task_id)
        except Exception:
            continue
    from ticktick_cli.exceptions import NotFoundError
    raise NotFoundError(f"Task {task_id} not found in any project.")
