"""Serializable state contract for reusable context panels."""

from dataclasses import dataclass, field

from PyQt6.QtCore import QDate


@dataclass
class ContextPanelState:
    week_monday: QDate | None = None
    date_filter: str | None = None
    tags: list[str] = field(default_factory=list)
    notebook_ids: list[int] = field(default_factory=list)
    forced_records: list[dict] = field(default_factory=list)
    sync_enabled: bool = True
    collapsed: bool = False

    def as_dict(self):
        return {
            "current_week_monday": self.week_monday.toString("yyyy-MM-dd") if self.week_monday else None,
            "current_date_filter": self.date_filter,
            "active_global_tags": list(self.tags),
            "notebook_ids": list(self.notebook_ids),
            "forced_records": [dict(record) for record in self.forced_records],
            "sync_enabled": self.sync_enabled,
            "collapsed": self.collapsed,
        }


def state_from_dict(value):
    value = value or {}
    monday_text = value.get("current_week_monday")
    monday = QDate.fromString(str(monday_text or ""), "yyyy-MM-dd") if monday_text else QDate()
    return ContextPanelState(
        week_monday=monday if monday.isValid() else None,
        date_filter=str(value["current_date_filter"]) if value.get("current_date_filter") else None,
        tags=[str(tag).strip() for tag in value.get("active_global_tags") or [] if str(tag).strip()],
        notebook_ids=list(value.get("notebook_ids") or []),
        forced_records=[dict(record) for record in value.get("forced_records") or []],
        sync_enabled=bool(value.get("sync_enabled", True)),
        collapsed=bool(value.get("collapsed", False)),
    )


def status_labels(state):
    if state.week_monday:
        date_label = f"Dates: {state.week_monday.toString('yyyy-MM-dd')} to {state.date_filter}"
    elif state.date_filter:
        date_label = f"Date: {state.date_filter}"
    else:
        date_label = "Dates: all history"
    return date_label, f"Tags: {', '.join(state.tags) if state.tags else 'all'}"
