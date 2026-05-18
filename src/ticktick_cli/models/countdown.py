"""Countdown model — Pydantic v2."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


COUNTDOWN_TYPE_MAP = {
    "countdown": 0,
    "anniversary": 1,
    "birthday": 2,
}
COUNTDOWN_TYPE_REVERSE = {0: "countdown", 1: "anniversary", 2: "birthday"}


class Countdown(BaseModel):
    """Represents a TickTick countdown (countdown, anniversary, birthday)."""

    id: str = ""
    name: str = ""
    date: int = 0  # YYYYMMDD integer format
    type: int = 0  # 0=countdown, 1=anniversary, 2=birthday
    color: str | None = None
    remark: str | None = None
    repeat: str | None = None
    reminders: list[dict[str, Any]] = Field(default_factory=list)
    icon_res: str | None = Field(default=None, alias="iconRes")
    style: str | None = None
    date_display_format: str | None = Field(default=None, alias="dateDisplayFormat")
    show_age: bool = Field(default=False, alias="showAge")
    sort_order: int | None = Field(default=None, alias="sortOrder")
    ignore_year: bool = Field(default=False, alias="ignoreYear")
    pinned: bool = False
    background: str | None = None
    created_time: str | None = Field(default=None, alias="createdTime")
    modified_time: str | None = Field(default=None, alias="modifiedTime")

    model_config = {"populate_by_name": True, "extra": "allow"}

    @property
    def date_label(self) -> str:
        """Format the integer date as YYYY-MM-DD."""
        if not self.date:
            return ""
        try:
            s = str(self.date)
            return f"{s[:4]}-{s[4:6]}-{s[6:8]}"
        except (IndexError, ValueError):
            return str(self.date)

    @property
    def type_label(self) -> str:
        """Human-readable type."""
        return COUNTDOWN_TYPE_REVERSE.get(self.type, "countdown")

    def to_output(self) -> dict[str, Any]:
        """Serialize for CLI output."""
        return {
            "id": self.id,
            "name": self.name,
            "type": self.type_label,
            "date": self.date_label,
            "color": self.color or "",
            "remark": self.remark or "",
            "repeat": self.repeat or "",
            "reminders": self.reminders,
            "icon": self.icon_res or "",
            "style": self.style or "",
            "dateFormat": self.date_display_format or "",
            "showAge": self.show_age,
            "sortOrder": self.sort_order,
            "ignoreYear": self.ignore_year,
            "pinned": self.pinned,
            "background": self.background or "",
        }
