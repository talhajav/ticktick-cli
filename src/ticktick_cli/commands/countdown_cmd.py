"""Countdown commands — list, create, edit, delete."""

from __future__ import annotations

import click

from ticktick_cli.auth import get_client
from ticktick_cli.models.countdown import Countdown, COUNTDOWN_TYPE_MAP
from ticktick_cli.output import (
    is_dry_run,
    output_dry_run,
    output_error,
    output_existing_item,
    output_item,
    output_list,
    output_message,
)


@click.group("countdown")
def countdown_group() -> None:
    """Manage countdowns, anniversaries, and birthdays."""


@countdown_group.command("list")
@click.pass_context
def countdown_list(ctx: click.Context) -> None:
    """List all countdowns."""
    client = get_client(ctx.obj.get("profile", "default"))
    try:
        raw = client.v2.get_countdowns()
        items = [Countdown(**c).to_output() for c in raw]
        output_list(
            items,
            columns=["id", "name", "type", "date", "remark"],
            title="Countdowns",
            ctx=ctx,
        )
    except Exception as e:
        output_error(str(e), ctx)
        raise SystemExit(1) from None


@countdown_group.command("create")
@click.argument("name")
@click.option("--date", required=True, help="Target date YYYY-MM-DD")
@click.option(
    "--type", "ctype",
    type=click.Choice(["countdown", "anniversary", "birthday"]),
    default="countdown",
    help="Countdown type",
)
@click.option("--color", default=None, help="Color (e.g., #FF6161)")
@click.option("--remark", default=None, help="Description / remark")
@click.option("--repeat", default=None, help="Recurrence RRULE")
@click.option("--reminder", multiple=True, help="Reminder trigger (repeatable)")
@click.option("--icon", default=None, help="Icon resource name")
@click.option("--style", type=click.Choice(["normal", "timer"]), default=None)
@click.option(
    "--date-format",
    type=click.Choice(["day", "week", "month"]),
    default=None,
    help="Date display format",
)
@click.option("--show-age", is_flag=True, default=None, help="Show age counter")
@click.option("--sort-order", type=int, default=None, help="Manual sort position")
@click.option("--ignore-year", is_flag=True, default=None, help="Ignore year (for birthdays)")
@click.option("--pinned", is_flag=True, default=None, help="Pin to top")
@click.option("--background", default=None, help="Background styling")
@click.option(
    "--if-not-exists", "if_not_exists", is_flag=True,
    help="Skip if countdown with same name exists",
)
@click.pass_context
def countdown_create(
    ctx: click.Context,
    name: str,
    date: str,
    ctype: str,
    color: str | None,
    remark: str | None,
    repeat: str | None,
    reminder: tuple[str, ...],
    icon: str | None,
    style: str | None,
    date_format: str | None,
    show_age: bool | None,
    sort_order: int | None,
    ignore_year: bool | None,
    pinned: bool | None,
    background: str | None,
    if_not_exists: bool,
) -> None:
    """Create a new countdown."""
    from ticktick_cli.api.v2 import _generate_object_id

    # Convert YYYY-MM-DD to integer
    date_int = int(date.replace("-", ""))

    data: dict = {
        "name": name,
        "date": date_int,
        "type": COUNTDOWN_TYPE_MAP.get(ctype, 0),
    }
    if color:
        data["color"] = color
    if remark:
        data["remark"] = remark
    if repeat:
        data["repeat"] = repeat
    if reminder:
        data["reminders"] = [
            {"id": _generate_object_id(), "trigger": r} for r in reminder
        ]
    if icon:
        data["iconRes"] = icon
    if style:
        data["style"] = style
    if date_format:
        data["dateDisplayFormat"] = date_format
    if show_age is not None:
        data["showAge"] = show_age
    if sort_order is not None:
        data["sortOrder"] = sort_order
    if ignore_year is not None:
        data["ignoreYear"] = ignore_year
    if pinned is not None:
        data["pinned"] = pinned
    if background:
        data["background"] = background

    if is_dry_run(ctx):
        output_dry_run("countdown.create", data, ctx)
        return

    client = get_client(ctx.obj.get("profile", "default"))

    if if_not_exists:
        try:
            existing = client.v2.get_countdowns()
            for c in existing:
                if c.get("name", "").lower() == name.lower():
                    output_existing_item(Countdown(**c).to_output(), ctx)
                    return
        except Exception as e:
            output_error(str(e), ctx)
            raise SystemExit(1) from None

    try:
        data["id"] = _generate_object_id()
        client.v2.batch_countdowns(add=[data])
        output_message(f"Countdown created: {name}", ctx)
    except Exception as e:
        output_error(str(e), ctx)
        raise SystemExit(1) from None


@countdown_group.command("edit")
@click.argument("countdown_id")
@click.option("--name", default=None, help="New name")
@click.option("--date", default=None, help="New date YYYY-MM-DD")
@click.option(
    "--type", "ctype",
    type=click.Choice(["countdown", "anniversary", "birthday"]),
    default=None,
    help="New type",
)
@click.option("--color", default=None, help="New color")
@click.option("--remark", default=None, help="New remark")
@click.option("--repeat", default=None, help="New recurrence RRULE")
@click.option("--reminder", multiple=True, help="New reminders (replaces existing)")
@click.option("--icon", default=None, help="New icon")
@click.option("--style", type=click.Choice(["normal", "timer"]), default=None)
@click.option("--date-format", type=click.Choice(["day", "week", "month"]), default=None)
@click.option("--show-age/--no-show-age", default=None, help="Toggle age display")
@click.option("--sort-order", type=int, default=None)
@click.option("--ignore-year/--no-ignore-year", default=None)
@click.option("--pinned/--unpinned", default=None, help="Toggle pinned")
@click.option("--background", default=None)
@click.pass_context
def countdown_edit(
    ctx: click.Context,
    countdown_id: str,
    name: str | None,
    date: str | None,
    ctype: str | None,
    color: str | None,
    remark: str | None,
    repeat: str | None,
    reminder: tuple[str, ...],
    icon: str | None,
    style: str | None,
    date_format: str | None,
    show_age: bool | None,
    sort_order: int | None,
    ignore_year: bool | None,
    pinned: bool | None,
    background: str | None,
) -> None:
    """Edit a countdown's properties."""
    update: dict = {"id": countdown_id}
    if name:
        update["name"] = name
    if date:
        update["date"] = int(date.replace("-", ""))
    if ctype:
        update["type"] = COUNTDOWN_TYPE_MAP.get(ctype, 0)
    if color:
        update["color"] = color
    if remark is not None:
        update["remark"] = remark
    if repeat is not None:
        update["repeat"] = repeat
    if reminder:
        from ticktick_cli.api.v2 import _generate_object_id
        update["reminders"] = [
            {"id": _generate_object_id(), "trigger": r} for r in reminder
        ]
    if icon:
        update["iconRes"] = icon
    if style:
        update["style"] = style
    if date_format:
        update["dateDisplayFormat"] = date_format
    if show_age is not None:
        update["showAge"] = show_age
    if sort_order is not None:
        update["sortOrder"] = sort_order
    if ignore_year is not None:
        update["ignoreYear"] = ignore_year
    if pinned is not None:
        update["pinned"] = pinned
    if background is not None:
        update["background"] = background

    if is_dry_run(ctx):
        output_dry_run("countdown.edit", update, ctx)
        return

    client = get_client(ctx.obj.get("profile", "default"))
    try:
        client.v2.batch_countdowns(update=[update])
        output_message(f"Countdown {countdown_id} updated.", ctx)
    except Exception as e:
        output_error(str(e), ctx)
        raise SystemExit(1) from None


@countdown_group.command("delete")
@click.argument("countdown_id")
@click.option("--yes", is_flag=True, help="Skip confirmation")
@click.pass_context
def countdown_delete(ctx: click.Context, countdown_id: str, yes: bool) -> None:
    """Delete a countdown."""
    if is_dry_run(ctx):
        output_dry_run("countdown.delete", {"id": countdown_id}, ctx)
        return
    if not yes:
        click.confirm(f"Delete countdown {countdown_id}?", abort=True)
    client = get_client(ctx.obj.get("profile", "default"))
    try:
        client.v2.batch_countdowns(delete=[countdown_id])
        output_message(f"Countdown {countdown_id} deleted.", ctx)
    except Exception as e:
        output_error(str(e), ctx)
        raise SystemExit(1) from None
