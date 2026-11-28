import json
import math
import re
from collections import defaultdict
from datetime import date, datetime, time, timedelta, timezone
from graphlib import TopologicalSorter
from pathlib import PurePath
from typing import Any, Dict, List, Optional, Tuple
from zoneinfo import ZoneInfo
from fastapi import APIRouter, Depends, status, HTTPException, Request, UploadFile, File
from fastapi.templating import Jinja2Templates
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from app.models.users_model import User
from app.models.dashboard.Dashboard import Dashboard
from app.models.permissions_model import Permission
from app.core.auth import validate_user
from app.database import get_db
from app.config import BASE_DIR
from app.schemas.project_dashboard import AddNotes

router = APIRouter(prefix="/project_dashboard")

templates = Jinja2Templates(directory=BASE_DIR / "templates")

MAX_XER_UPLOAD_BYTES = 25 * 1024 * 1024
XER_HEADER_FIELDS = (
    "version",
    "export_date",
    "export_type",
    "export_user",
    "company",
    "database_name",
    "product_name",
    "currency",
)
DASHBOARD_KEYS = ("t", "cs", "pr", "gr", "MN", "BN", "v", "itn")
TRADE_NAMES = (
    "Masonry & Demolition",
    "Insulation & Waterproofing",
    "Plumbing",
    "HVAC",
    "Electrical & Light Current",
    "Plastering",
    "Gypsum Board",
    "Painting",
    "Flooring, Tiles & Marble",
    "Doors & Windows",
    "Joinery, Marble Tops & Glass",
    "Elevator Works",
    "Other",
)
TRADE_PATTERNS = (
    (re.compile(r"mason|demolit", re.I), TRADE_NAMES[0]),
    (re.compile(r"insulat|waterproof", re.I), TRADE_NAMES[1]),
    (re.compile(r"plumb|cistern|drain", re.I), TRADE_NAMES[2]),
    (re.compile(r"\bhvac\b|\bac\b|air.?condition|air.?grille|duct|ventilat|exhaust fan", re.I), TRADE_NAMES[3]),
    (re.compile(r"electric|electrical|light current|wiring device|intercom|lightning fixture", re.I), TRADE_NAMES[4]),
    (re.compile(r"plaster|render|screed", re.I), TRADE_NAMES[5]),
    (re.compile(r"gypsum", re.I), TRADE_NAMES[6]),
    (re.compile(r"paint|putty|primer|sealer", re.I), TRADE_NAMES[7]),
    (re.compile(r"door|window", re.I), TRADE_NAMES[9]),
    (re.compile(r"joinery|countertop|cabinet|wooden shelf|wooden drawer|wall niche|wall cladding|glass", re.I), TRADE_NAMES[10]),
    (re.compile(r"elevator|\blift\b", re.I), TRADE_NAMES[11]),
)
FLOORING_ITEM_PATTERNS = (
    (re.compile(r"\bspc\s+flooring\b", re.I), "SPC Flooring"),
    (re.compile(r"\bhdf\s+flooring\b", re.I), "HDF Flooring"),
    (re.compile(r"wallpaper", re.I), "Wallpaper"),
    (re.compile(r"ceramic\s+flooring\s+under\s+finishing\s+floor", re.I),
     "Ceramic · Floor under finishing"),
    (re.compile(r"wall\s+ceramic\s+tiles?\s+for\s+bathroom", re.I),
     "Ceramic · Bathroom walls"),
    (re.compile(r"floor\s+ceramic\s+tiles?", re.I), "Ceramic · Bathroom floors"),
    (re.compile(r"pushhammered\s+marble", re.I), "Marble · Pushhammered"),
    (re.compile(r"imported\s+marble\s+for\s+stairs", re.I),
     "Marble · Imported (stairs)"),
)
WORK_CATEGORIES = {
    "P": TRADE_NAMES[7],
    "F": TRADE_NAMES[8],
    "G": TRADE_NAMES[6],
}


def _number(value: Any) -> Optional[float]:
    if value is None or value == "":
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _xer_date(value: Any) -> Optional[date]:
    if not value:
        return None
    text = str(value).strip()
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).date()
    except ValueError:
        try:
            return date.fromisoformat(text[:10])
        except ValueError:
            return None


def _dashboard_progress(task: Dict[str, str]) -> float:
    if task.get("complete_pct_type") == "CP_Drtn":
        target_duration = _number(task.get("target_drtn_hr_cnt"))
        remaining_duration = _number(task.get("remain_drtn_hr_cnt"))
        if target_duration and target_duration > 0 and remaining_duration is not None:
            return min(1.0, max(0.0, 1 - remaining_duration / target_duration))

    value = _number(task.get("phys_complete_pct"))
    if value is not None:
        if value > 1:
            value /= 100
        return min(1.0, max(0.0, value))

    if "complete" in (task.get("status_code") or "").lower():
        return 1.0
    actual = _number(task.get("act_work_qty"))
    target = _number(task.get("target_work_qty"))
    if actual is not None and target and target > 0:
        return min(1.0, max(0.0, actual / target))
    return 0.0


def _parse_xer_calendar(row: Dict[str, str]) -> Dict[str, Any]:
    weekly_hours: Dict[int, List[Tuple[int, int]]] = {
        day: [] for day in range(1, 8)
    }
    exceptions: Dict[date, List[Tuple[int, int]]] = {}
    section = None
    current_day = None
    current_exception = None
    calendar_data = row.get("clndr_data") or ""

    for token in (part.strip() for part in calendar_data.split("\x7f") if part.strip()):
        if "DaysOfWeek()" in token:
            section = "weekly"
            current_day = None
            continue
        if "Exceptions()" in token:
            section = "exceptions"
            current_exception = None
            continue
        if "VIEW(" in token:
            section = None
            continue

        if section == "weekly":
            day_match = re.search(r"\|\|([1-7])\(\)", token)
            if day_match:
                current_day = int(day_match.group(1))
        elif section == "exceptions":
            date_match = re.search(r"\|\|\d+\(d\|(\d+)\)", token)
            if date_match:
                current_exception = date(1899, 12, 30) + timedelta(
                    days=int(date_match.group(1))
                )
                exceptions[current_exception] = []

        periods = re.findall(r"s\|(\d{2}):(\d{2})\|f\|(\d{2}):(\d{2})", token)
        if periods:
            parsed_periods = [
                (int(start_hour) * 60 + int(start_minute),
                 int(end_hour) * 60 + int(end_minute))
                for start_hour, start_minute, end_hour, end_minute in periods
            ]
            if section == "weekly" and current_day is not None:
                weekly_hours[current_day].extend(parsed_periods)
            elif section == "exceptions" and current_exception is not None:
                exceptions[current_exception].extend(parsed_periods)

    if "DaysOfWeek()" not in calendar_data:
        raise ValueError(f"XER calendar {row.get('clndr_id', '')} has no weekly schedule")
    return {"weekly": weekly_hours, "exceptions": exceptions}


def _calendar_prefix(
    calendar: Dict[str, Any],
    start: date,
    finish: date,
) -> Dict[date, float]:
    prefix = {start: 0.0}
    current = start
    while current < finish:
        periods = calendar["exceptions"].get(
            current,
            calendar["weekly"].get(((current.weekday() + 1) % 7) + 1, []),
        )
        hours = sum(end - begin for begin, end in periods) / 60
        next_day = current + timedelta(days=1)
        prefix[next_day] = prefix[current] + hours
        current = next_day
    return prefix


def _planned_progress(
    start: Optional[date],
    finish: Optional[date],
    data_date: Optional[date],
    fallback: float,
    working_hours: Optional[Dict[date, float]] = None,
) -> float:
    if not start or not finish or not data_date:
        return fallback
    duration = (finish - start).days
    if duration <= 0:
        return 1.0 if data_date >= finish else 0.0
    if working_hours is not None:
        total = working_hours[finish] - working_hours[start]
        if total <= 0:
            return 1.0 if data_date >= finish else 0.0
        cutoff = min(finish, max(start, data_date))
        elapsed = working_hours[cutoff] - working_hours[start]
        return min(1.0, max(0.0, elapsed / total))
    return min(1.0, max(0.0, (data_date - start).days / duration))


def _xer_datetime(value: Any) -> Optional[datetime]:
    if not value:
        return None
    text = str(value).strip()
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        parsed_date = _xer_date(text)
        return datetime.combine(parsed_date, time()) if parsed_date else None
    return parsed.replace(tzinfo=None) if parsed.tzinfo else parsed


def _calendar_periods(calendar: Dict[str, Any], day: date) -> List[Tuple[int, int]]:
    day_number = ((day.weekday() + 1) % 7) + 1
    return calendar["exceptions"].get(day, calendar["weekly"].get(day_number, []))


def _align_to_work_time(
    calendar: Dict[str, Any],
    value: datetime,
    forward: bool = True,
) -> datetime:
    current_day = value.date()
    for _ in range(3660):
        periods = _calendar_periods(calendar, current_day)
        if forward:
            for begin, end in periods:
                period_start = datetime.combine(current_day, time()) + timedelta(minutes=begin)
                period_end = datetime.combine(current_day, time()) + timedelta(minutes=end)
                candidate = max(value, period_start)
                if candidate < period_end:
                    return candidate
            current_day += timedelta(days=1)
            value = datetime.combine(current_day, time())
        else:
            for begin, end in reversed(periods):
                period_start = datetime.combine(current_day, time()) + timedelta(minutes=begin)
                period_end = datetime.combine(current_day, time()) + timedelta(minutes=end)
                candidate = min(value, period_end)
                if candidate > period_start:
                    return candidate
            current_day -= timedelta(days=1)
            value = datetime.combine(current_day, time(23, 59, 59))
    raise ValueError("XER calendar has no working time within ten years")


def _add_working_hours(
    calendar: Dict[str, Any],
    value: datetime,
    hours: float,
) -> datetime:
    if hours < 0:
        return _subtract_working_hours(calendar, value, -hours)

    current = _align_to_work_time(calendar, value)
    remaining = hours * 60
    if remaining == 0:
        return current

    for _ in range(3660):
        for begin, end in _calendar_periods(calendar, current.date()):
            period_start = datetime.combine(current.date(), time()) + timedelta(minutes=begin)
            period_end = datetime.combine(current.date(), time()) + timedelta(minutes=end)
            start = max(current, period_start)
            if start >= period_end:
                continue
            available = (period_end - start).total_seconds() / 60
            if remaining <= available:
                return start + timedelta(minutes=remaining)
            remaining -= available
        current = _align_to_work_time(
            calendar,
            datetime.combine(current.date() + timedelta(days=1), time()),
        )
    raise ValueError("XER activity duration exceeds ten years of calendar time")


def _subtract_working_hours(
    calendar: Dict[str, Any],
    value: datetime,
    hours: float,
) -> datetime:
    current = _align_to_work_time(calendar, value, forward=False)
    remaining = hours * 60
    if remaining == 0:
        return current

    for _ in range(3660):
        for begin, end in reversed(_calendar_periods(calendar, current.date())):
            period_start = datetime.combine(current.date(), time()) + timedelta(minutes=begin)
            period_end = datetime.combine(current.date(), time()) + timedelta(minutes=end)
            stop = min(current, period_end)
            if stop <= period_start:
                continue
            available = (stop - period_start).total_seconds() / 60
            if remaining <= available:
                return stop - timedelta(minutes=remaining)
            remaining -= available
        previous_day = current.date() - timedelta(days=1)
        current = _align_to_work_time(
            calendar,
            datetime.combine(previous_day, time(23, 59, 59)),
            forward=False,
        )
    raise ValueError("XER relationship lag exceeds ten years of calendar time")


def _working_hours_between(
    calendar: Dict[str, Any],
    start: datetime,
    finish: datetime,
) -> float:
    if finish <= start:
        return 0.0
    total_minutes = 0.0
    current_day = start.date()
    while current_day <= finish.date():
        for begin, end in _calendar_periods(calendar, current_day):
            period_start = datetime.combine(current_day, time()) + timedelta(minutes=begin)
            period_end = datetime.combine(current_day, time()) + timedelta(minutes=end)
            total_minutes += max(
                0.0,
                (min(finish, period_end) - max(start, period_start)).total_seconds() / 60,
            )
        current_day += timedelta(days=1)
    return total_minutes / 60


def _rebuild_baseline_schedule(
    tables: Dict[str, Any],
    tasks: List[Dict[str, str]],
    calendars: Dict[str, Dict[str, Any]],
    project: Dict[str, str],
) -> Dict[str, Tuple[datetime, datetime]]:
    project_start = _xer_datetime(project.get("plan_start_date"))
    if not project_start:
        raise ValueError("XER project has no valid planned start date")
    project_calendar_id = project.get("clndr_id")
    if project_calendar_id not in calendars:
        raise ValueError("XER project calendar is missing")

    tasks_by_id = {
        task.get("task_id"): task
        for task in tasks
        if task.get("task_id")
    }
    if len(tasks_by_id) != len(tasks):
        raise ValueError("XER activities have missing or duplicate IDs")

    calendar_ids = {}
    durations = {}
    for task_id, task in tasks_by_id.items():
        calendar_id = task.get("clndr_id") or project_calendar_id
        duration = _number(task.get("target_drtn_hr_cnt"))
        if calendar_id not in calendars:
            raise ValueError(f"XER activity {task_id} has no valid calendar")
        if duration is None or duration < 0:
            raise ValueError(f"XER activity {task_id} has no valid original duration")
        calendar_ids[task_id] = calendar_id
        durations[task_id] = duration

    predecessors = {task_id: set() for task_id in tasks_by_id}
    incoming = defaultdict(list)
    for relationship in tables.get("TASKPRED", []):
        predecessor_id = relationship.get("pred_task_id")
        successor_id = relationship.get("task_id")
        if predecessor_id not in tasks_by_id or successor_id not in tasks_by_id:
            raise ValueError("XER activity relationship references an unknown activity")
        predecessors[successor_id].add(predecessor_id)
        incoming[successor_id].append(relationship)

    order = TopologicalSorter(predecessors).static_order()
    starts: Dict[str, datetime] = {}
    finishes: Dict[str, datetime] = {}
    for task_id in order:
        task = tasks_by_id[task_id]
        calendar = calendars[calendar_ids[task_id]]
        duration = durations[task_id]
        candidate = _align_to_work_time(calendar, project_start)
        if task.get("cstr_type") == "CS_MSO":
            constraint_date = _xer_datetime(task.get("cstr_date"))
            if constraint_date:
                candidate = max(candidate, _align_to_work_time(calendar, constraint_date))

        for relationship in incoming[task_id]:
            predecessor_id = relationship["pred_task_id"]
            predecessor_start = starts[predecessor_id]
            predecessor_finish = finishes[predecessor_id]
            lag_calendar = calendars[calendar_ids[predecessor_id]]
            lag = _number(relationship.get("lag_hr_cnt")) or 0.0
            relationship_type = relationship.get("pred_type")
            if relationship_type == "PR_FS":
                bound = _add_working_hours(lag_calendar, predecessor_finish, lag)
            elif relationship_type == "PR_SS":
                bound = _add_working_hours(lag_calendar, predecessor_start, lag)
            elif relationship_type == "PR_FF":
                required_finish = (
                    predecessor_finish
                    if lag == 0
                    else _add_working_hours(lag_calendar, predecessor_finish, lag)
                )
                bound = _subtract_working_hours(calendar, required_finish, duration)
            elif relationship_type == "PR_SF":
                required_finish = (
                    predecessor_start
                    if lag == 0
                    else _add_working_hours(lag_calendar, predecessor_start, lag)
                )
                bound = _subtract_working_hours(calendar, required_finish, duration)
            else:
                raise ValueError(f"XER contains unsupported relationship type {relationship_type!r}")
            candidate = max(candidate, bound)

        start = _align_to_work_time(calendar, candidate)
        starts[task_id] = start
        finishes[task_id] = _add_working_hours(calendar, start, duration)

    return {
        task_id: (starts[task_id], finishes[task_id])
        for task_id in tasks_by_id
    }


def _flooring_item_name(name: str) -> Optional[str]:
    for pattern, item_name in FLOORING_ITEM_PATTERNS:
        if pattern.search(name):
            return item_name
    return None


def _activity_trade(name: str) -> str:
    if _flooring_item_name(name):
        return TRADE_NAMES[8]
    for pattern, trade in TRADE_PATTERNS:
        if pattern.search(name):
            return trade
    return TRADE_NAMES[-1]


def _activity_component(text: str) -> str:
    return "pr" if re.search(r"procure|purchas|deliver|supplier|vendor|material", text, re.I) else "c"


def _villa_name(text: str) -> Optional[str]:
    match = re.search(r"\bVilla(?!s)\s+(\d+[A-Za-z]?)(?:\s*(Left|Right|L|R))?\b", text, re.I)
    if not match:
        return None
    name = "Villa " + match.group(1)
    side = match.group(2)
    if side:
        name += " " + ({"l": "Left", "r": "Right"}.get(side.lower(), side.title()))
    return name


def _metric(records: List[Dict[str, Any]]) -> Dict[str, float]:
    return {
        "b": round(sum(record["b"] for record in records), 2),
        "p": round(sum(record["p"] for record in records), 2),
        "e": round(sum(record["e"] for record in records), 2),
    }


def _finite_dashboard_values(value: Any) -> Any:
    if isinstance(value, float) and not math.isfinite(value):
        return 0.0
    if isinstance(value, dict):
        return {key: _finite_dashboard_values(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_finite_dashboard_values(item) for item in value]
    return value


def build_dashboard_data(data: Any) -> Dict[str, Any]:
    """Return the template payload, spreading activity target costs over XER calendars."""
    if isinstance(data, dict) and all(key in data for key in DASHBOARD_KEYS):
        if (
            isinstance(data["t"], dict)
            and isinstance(data["cs"], dict)
            and isinstance(data["pr"], dict)
            and isinstance(data["gr"], list)
            and isinstance(data["v"], list)
            and isinstance(data["MN"], (dict, list))
            and isinstance(data["BN"], (dict, list))
            and isinstance(data["itn"], dict)
        ):
            return _finite_dashboard_values(data)

    if not isinstance(data, dict) or not isinstance(data.get("tables"), dict):
        raise ValueError("Stored dashboard data is neither chart-ready nor a parsed XER export")

    tables = data["tables"]
    tasks = tables.get("TASK")
    if not isinstance(tasks, list) or not tasks:
        raise ValueError("XER export contains no activities to display")

    wbs_rows = tables.get("PROJWBS", [])
    if not isinstance(wbs_rows, list):
        raise ValueError("XER export contains an invalid WBS table")
    wbs_by_id = {
        row.get("wbs_id"): row
        for row in wbs_rows
        if isinstance(row, dict) and row.get("wbs_id")
    }
    roots = {
        row.get("wbs_id")
        for row in wbs_rows
        if isinstance(row, dict) and row.get("proj_node_flag") == "Y"
    }

    def wbs_path(wbs_id: Optional[str]) -> List[Dict[str, str]]:
        path = []
        seen = set()
        while wbs_id in wbs_by_id and wbs_id not in seen:
            seen.add(wbs_id)
            row = wbs_by_id[wbs_id]
            path.append(row)
            wbs_id = row.get("parent_wbs_id")
        return list(reversed(path))

    assignment_costs = defaultdict(float)
    for assignment in tables.get("TASKRSRC", []):
        if not isinstance(assignment, dict):
            continue
        task_id = assignment.get("task_id")
        amount = _number(assignment.get("target_cost"))
        if task_id and amount is not None:
            assignment_costs[task_id] += amount

    # Use the first-level WBS branches as groups only when the export clearly
    # uses them to divide residential/group work.
    branch_rows = {}
    for task in tasks:
        if not isinstance(task, dict):
            continue
        path = wbs_path(task.get("wbs_id"))
        for index, row in enumerate(path):
            if row.get("wbs_id") in roots:
                if index + 1 < len(path):
                    branch = path[index + 1]
                    branch_rows[branch.get("wbs_id")] = branch
                break
    branch_names = [
        row.get("wbs_name") or row.get("wbs_short_name") or ""
        for row in branch_rows.values()
    ]
    use_branches = (
        2 <= len(branch_rows) <= 4
        and all(re.search(r"villa|house|group|cluster", name, re.I) for name in branch_names)
    )
    ordered_branches = sorted(
        branch_rows.items(),
        key=lambda item: (
            _number(item[1].get("seq_num")) is None,
            _number(item[1].get("seq_num")) or 0,
            item[0] or "",
        ),
    )
    branch_groups = {
        branch_id: index
        for index, (branch_id, _) in enumerate(ordered_branches, start=1)
    } if use_branches else {}

    header = data.get("header")
    project_rows = tables.get("PROJECT", [])
    project = project_rows[0] if isinstance(project_rows, list) and project_rows else None
    project_data_date = _xer_datetime(project.get("last_recalc_date")) if project else None
    data_date_time = project_data_date or (
        _xer_datetime(header.get("export_date")) if isinstance(header, dict) else None
    )
    data_date = data_date_time.date() if data_date_time else None
    calendar_rows = tables.get("CALENDAR", [])
    if not isinstance(calendar_rows, list):
        raise ValueError("XER export contains an invalid calendar table")
    calendars_by_id = {
        row.get("clndr_id"): _parse_xer_calendar(row)
        for row in calendar_rows
        if isinstance(row, dict) and row.get("clndr_id")
    }
    baseline_schedules = (
        _rebuild_baseline_schedule(tables, tasks, calendars_by_id, project)
        if project
        else {}
    )
    task_schedules = {
        task.get("task_id"): (
            (
                baseline_schedules[task.get("task_id")][0].date(),
                baseline_schedules[task.get("task_id")][1].date(),
            )
            if task.get("task_id") in baseline_schedules
            else (
                _xer_date(task.get("target_start_date")),
                _xer_date(task.get("target_end_date")),
            )
        ) + (
            task.get("clndr_id"),
        )
        for task in tasks
        if isinstance(task, dict) and task.get("task_id")
    }
    dated_schedules = [
        (start, finish)
        for start, finish, _ in task_schedules.values()
        if start and finish and finish >= start
    ]
    calendar_prefixes: Dict[str, Dict[date, float]] = {}
    if dated_schedules:
        schedule_start = min(start for start, _ in dated_schedules)
        schedule_finish = max(finish for _, finish in dated_schedules)
        used_calendar_ids = {
            calendar_id
            for _, _, calendar_id in task_schedules.values()
            if calendar_id in calendars_by_id
        }
        for calendar_id in used_calendar_ids:
            calendar = calendars_by_id[calendar_id]
            calendar_prefixes[calendar_id] = _calendar_prefix(
                calendar,
                schedule_start,
                schedule_finish,
            )
    records = []
    group_labels = {index: f"Group {index}" for index in range(1, 5)}
    for task in tasks:
        if not isinstance(task, dict):
            continue
        task_id = task.get("task_id")
        path = wbs_path(task.get("wbs_id"))
        path_names = [
            row.get("wbs_name") or row.get("wbs_short_name") or ""
            for row in path
        ]
        name = task.get("task_name") or task.get("task_code") or str(task_id or "Activity")
        path_text = " ".join(path_names)
        group_match = re.search(r"\b(?:group|grp|g|phase)\s*[-_#:]?\s*(\d+)\b", path_text, re.I)
        branch_id = None
        for index, row in enumerate(path):
            if row.get("wbs_id") in roots and index + 1 < len(path):
                branch_id = path[index + 1].get("wbs_id")
                break
        if group_match:
            group_number = int(group_match.group(1))
            group_index = min(group_number, 4)
            group_labels[group_index] = (
                f"Group {group_index}" if group_number <= 4 else "Other groups"
            )
        elif branch_id in branch_groups:
            group_index = branch_groups[branch_id]
            group_labels[group_index] = (
                path_names[1] if len(path_names) > 1 else f"Group {group_index}"
            )
        else:
            group_index = 1

        villa = _villa_name(path_text) or _villa_name(name)
        text = f"{path_text} {name}"
        component = _activity_component(text)
        progress = _dashboard_progress(task)
        start, finish, calendar_id = task_schedules.get(
            task_id,
            (
                _xer_date(task.get("target_start_date")),
                _xer_date(task.get("target_end_date")),
                task.get("clndr_id"),
            ),
        )
        forecast_finish = _xer_date(task.get("early_end_date")) or finish
        budget = assignment_costs.get(task_id)
        if budget is None or budget == 0:
            budget = _number(task.get("target_cost"))
        budget = max(0.0, budget or 0.0)
        if task_id in baseline_schedules and data_date_time:
            baseline_start, baseline_finish = baseline_schedules[task_id]
            calendar = calendars_by_id[calendar_id or project.get("clndr_id")]
            duration = _working_hours_between(calendar, baseline_start, baseline_finish)
            elapsed = _working_hours_between(
                calendar,
                baseline_start,
                min(baseline_finish, data_date_time),
            )
            plan = (
                min(1.0, max(0.0, elapsed / duration))
                if duration > 0
                else (1.0 if data_date_time >= baseline_finish else 0.0)
            )
        else:
            plan = _planned_progress(
                start,
                finish,
                data_date,
                progress,
                calendar_prefixes.get(calendar_id),
            )
        trade = _activity_trade(name)
        category = next(
            (key for key, category_trade in WORK_CATEGORIES.items() if category_trade == trade),
            None,
        )
        item_name = _flooring_item_name(name) or name
        records.append(
            {
                "name": str(name),
                "item_name": item_name,
                "g": group_index,
                "villa": villa,
                "component": component,
                "trade": trade,
                "category": category,
                "b": budget,
                "p": budget * plan,
                "e": budget * progress,
                "progress": progress,
                "active": (task.get("status_code") or "").lower().endswith("active"),
                "start": start,
                "finish": finish,
                "forecast_finish": forecast_finish,
            }
        )

    if not any(record["b"] > 0 for record in records):
        raise ValueError("XER export has no activity or resource-assignment budget costs")

    has_villas = any(record["villa"] for record in records)
    group_records = {
        index: [record for record in records if record["g"] == index]
        for index in range(1, 5)
    }
    group_data = []
    for index in range(1, 5):
        group_records_for_index = group_records[index]
        group_data.append(
            {
                "n": group_labels[index],
                "c": _metric([record for record in group_records_for_index if record["component"] == "c"]),
                "p": _metric([record for record in group_records_for_index if record["component"] == "pr"]),
            }
        )

    unit_records = defaultdict(list)
    for record in records:
        if record["component"] != "c":
            continue
        if has_villas and not record["villa"]:
            continue
        unit = record["villa"] or "Project"
        unit_records[(record["g"], unit)].append(record)

    item_names = {
        category: sorted(
            {
                record["item_name"]
                for record in records
                if record["component"] == "c" and record["category"] == category
            }
        )
        for category in WORK_CATEGORIES
    }
    villa_data = []
    for (group_index, unit), unit_tasks in sorted(
        unit_records.items(), key=lambda item: (item[0][0], item[0][1].casefold())
    ):
        trade_tasks = defaultdict(list)
        items = defaultdict(lambda: defaultdict(lambda: [0.0, 0.0]))
        for record in unit_tasks:
            trade_tasks[record["trade"]].append(record)
            if record["category"]:
                totals = items[record["category"]][record["item_name"]]
                totals[0] += record["b"]
                totals[1] += record["e"]

        trades = []
        for trade in TRADE_NAMES:
            grouped = trade_tasks.get(trade, [])
            if not grouped:
                continue
            total_budget = sum(record["b"] for record in grouped)
            total_earned = sum(record["e"] for record in grouped)
            avg_progress = sum(record["progress"] for record in grouped) / len(grouped)
            ratio = total_earned / total_budget if total_budget else avg_progress
            if all(record["progress"] >= 1 for record in grouped):
                status_text = "Completed"
            elif any(record["active"] for record in grouped):
                status_text = "In Progress"
            elif any(record["progress"] > 0 for record in grouped):
                status_text = "Waiting"
            else:
                status_text = "Not Started"

            delayed = [
                record
                for record in grouped
                if data_date and record["finish"] and record["finish"] < data_date and record["progress"] < 1
            ]
            delay_days = [
                (data_date - record["finish"]).days
                for record in delayed
                if data_date and record["finish"]
            ]
            pending_names = [
                record["name"] for record in grouped if record["progress"] < 1
            ]
            trades.append(
                [
                    trade,
                    ratio,
                    status_text,
                    len(delayed),
                    max(delay_days, default=0),
                    "; ".join(pending_names) or "-",
                    round(total_budget, 2),
                ]
            )

        ordered_tasks = sorted(
            unit_tasks,
            key=lambda record: (record["start"] or date.max, record["name"].casefold()),
        )
        completed = [record for record in ordered_tasks if record["progress"] >= 1]
        incomplete = [record for record in ordered_tasks if record["progress"] < 1]
        main_index = {name: index for index, name in enumerate(TRADE_NAMES, start=1)}

        def stage_index(record: Dict[str, Any]) -> int:
            return main_index.get(record["trade"], len(TRADE_NAMES) + 1)

        next_task = incomplete[0] if incomplete else None
        main_next = (
            [
                stage_index(next_task),
                next_task["name"],
                bool(next_task["start"] and data_date and next_task["start"] > data_date),
            ]
            if next_task
            else None
        )
        bathroom_tasks = [
            record
            for record in ordered_tasks
            if re.search(r"bath|shower|ensuite|wc", record["name"], re.I)
        ]
        bathroom_completed = [
            record for record in bathroom_tasks if record["progress"] >= 1
        ]
        bathroom_incomplete = [
            record for record in bathroom_tasks if record["progress"] < 1
        ]
        bathroom_next_task = bathroom_incomplete[0] if bathroom_incomplete else None
        bathroom_next = (
            [
                stage_index(bathroom_next_task),
                bathroom_next_task["name"],
                bool(
                    bathroom_next_task["start"]
                    and data_date
                    and bathroom_next_task["start"] > data_date
                ),
            ]
            if bathroom_next_task
            else None
        )
        delayed_tasks = [
            record
            for record in unit_tasks
            if data_date and record["finish"] and record["finish"] < data_date and record["progress"] < 1
        ]
        baseline_finish = max(
            (record["finish"] for record in unit_tasks if record["finish"]),
            default=None,
        )
        forecast_finish = max(
            (record["forecast_finish"] for record in unit_tasks if record["forecast_finish"]),
            default=baseline_finish,
        )
        item_data = {
            category: [
                [name, *items[category][name]]
                for name in item_names[category]
            ]
            for category in WORK_CATEGORIES
        }
        incomplete_candidates = [
            record for record in ordered_tasks if record["progress"] < 1
        ][:3]
        villa_data.append(
            {
                "n": unit,
                "g": f"G{group_index}",
                **_metric(unit_tasks),
                "dl": len(delayed_tasks),
                "md": max(
                    ((data_date - record["finish"]).days for record in delayed_tasks),
                    default=0,
                ),
                "var": (forecast_finish - baseline_finish).days
                if forecast_finish and baseline_finish
                else 0,
                "bl": baseline_finish.strftime("%d-%b-%y") if baseline_finish else "–",
                "fc": forecast_finish.strftime("%d-%b-%y") if forecast_finish else "–",
                "tr": trades,
                "pu": [
                    [
                        record["name"],
                        f"{record['progress'] * 100:.0f}%" if record["progress"] else "Not started",
                        max(0, (record["start"] - data_date).days)
                        if record["start"] and data_date
                        else 0,
                        max(0, (record["finish"] - record["start"]).days)
                        if record["start"] and record["finish"]
                        else 0,
                        bool(record["start"] and data_date and record["start"] > data_date),
                    ]
                    for record in incomplete_candidates
                ],
                "mc": stage_index(completed[-1]) if completed else 0,
                "mn": main_next,
                "mo": [
                    [stage_index(record), round(record["progress"] * 100)]
                    for record in incomplete[1:6]
                ],
                "bc": stage_index(bathroom_completed[-1]) if bathroom_completed else 0,
                "bn": bathroom_next,
                "bo": [],
                "why": [],
                "elev": any("elevator" in record["name"].lower() for record in unit_tasks),
                "it": item_data,
            }
        )

    all_records = records
    construction = [record for record in records if record["component"] == "c"]
    procurement = [record for record in records if record["component"] == "pr"]
    return {
        "t": _metric(all_records),
        "cs": _metric(construction),
        "pr": _metric(procurement),
        "gr": group_data,
        "MN": ["", *TRADE_NAMES],
        "BN": ["", *TRADE_NAMES],
        "v": villa_data,
        "itn": item_names,
    }


def parse_xer(
    content: bytes,
) -> Tuple[Dict[str, Any], Dict[str, List[Dict[str, str]]]]:
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError:
        try:
            text = content.decode("cp1252")
        except UnicodeDecodeError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="XER file must use UTF-8 or Windows-1252 encoding",
            ) from exc

    lines = re.split(r"\r\n|\n|\r", text)
    if not lines or not lines[0].startswith("ERMHDR\t"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is not a valid XER export",
        )

    header_values = lines[0].split("\t")[1:]
    if len(header_values) < len(XER_HEADER_FIELDS):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="XER header is incomplete",
        )
    header = dict(zip(XER_HEADER_FIELDS, header_values))
    header["raw_fields"] = header_values

    tables: Dict[str, List[Dict[str, str]]] = {}
    table_fields: Dict[str, List[str]] = {}
    table_name: Optional[str] = None
    fields: Optional[List[str]] = None
    ended = False

    for line_number, line in enumerate(lines[1:], start=2):
        if not line:
            continue
        if line == "%E":
            if table_name is not None and fields is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="XER table is missing its field header",
                )
            ended = True
            if any(remaining.strip() for remaining in lines[line_number:]):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Unexpected content after the XER end marker",
                )
            break
        if line.startswith("%T\t"):
            if table_name is not None and fields is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"XER table is missing its field header at line {line_number}",
                )
            table_name = line[3:]
            if not table_name or table_name in tables:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid or duplicate XER table at line {line_number}",
                )
            tables[table_name] = []
            fields = None
        elif line.startswith("%F\t"):
            if table_name is None or fields is not None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Unexpected XER field header at line {line_number}",
                )
            fields = line[3:].split("\t")
            if not fields or any(not field for field in fields) or len(set(fields)) != len(fields):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid XER fields at line {line_number}",
                )
            table_fields[table_name] = fields
        elif line.startswith("%R\t"):
            if table_name is None or fields is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"XER record appears before its field header at line {line_number}",
                )
            values = line[3:].split("\t")
            if len(values) != len(fields):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"XER record has an invalid field count at line {line_number}",
                )
            tables[table_name].append(dict(zip(fields, values)))
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unrecognized XER record at line {line_number}",
            )

    if (
        not ended
        or len(tables.get("PROJECT", [])) != 1
        or not tables.get("PROJWBS")
        or not tables.get("TASK")
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="XER export must contain one project, WBS data, task data, and an end marker",
        )

    header["table_fields"] = table_fields
    return header, tables


@router.get("/")
def get_projects(request: Request, db: Session = Depends(get_db)):

    token = request.cookies.get("access_token")
    user_id, user_role = validate_user(token)
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    if user.role != "super_admin":
        permission = db.query(Permission).filter(Permission.user_id == user_id,
                                                 Permission.type == "manage dashboards").first()
        if not permission:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

    dashboards = db.query(Dashboard).order_by(Dashboard.uploaded_at.desc()).all()

    return [
        {
            "id": d.id,
            "project_name": d.project_name,
            "uploaded_at": d.uploaded_at,
        }
        for d in dashboards
    ]

@router.get("/details/{dashboard_id}")
def get_project_details(request: Request, dashboard_id: int, db: Session = Depends(get_db)):

    token = request.cookies.get("access_token")
    user_id, user_role = validate_user(token)
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    if user.role != "super_admin":
        permission = db.query(Permission).filter(Permission.user_id == user_id,
                                                 Permission.type == "manage dashboards").first()
        if not permission:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

    dashboard_result = db.query(Dashboard, User).outerjoin(User, User.id == Dashboard.last_edited).filter(Dashboard.id == dashboard_id).first()
    dashboard, last_editor = dashboard_result
    if not dashboard:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    try:
        dashboard_data = build_dashboard_data(dashboard.data)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    metadata = [
        ("Export date", dashboard.export_date.isoformat() if dashboard.export_date else None),
        ("Uploaded", dashboard.uploaded_at.astimezone(ZoneInfo("Africa/Cairo"))),
        ("XER version", dashboard.xer_version),
        ("Export type", dashboard.export_type),
        ("Currency", dashboard.currency),
    ]
    details = [
        ("File", dashboard.filename),
        ("Export user", dashboard.export_user),
        ("Database", dashboard.database_name),
    ]
    if dashboard.row_counts is not None:
        details.append(("Row counts", json.dumps(dashboard.row_counts, ensure_ascii=False)))

    dashboard_meta = {
        "title": dashboard.project_name or dashboard.filename or f"Project Dashboard #{dashboard.id}",
        "subtitle": " · ".join(f"{label}: {value}" for label, value in metadata if value),
        "description": " · ".join(f"{label}: {value}" for label, value in details if value),
        "notes": dashboard.notes,
        "last_edited": f"{last_editor.first_name} {last_editor.last_name}" if last_editor is not None else None
    }

    return templates.TemplateResponse(
        "project_dashboard.html",
        {
            "request": request,
            "dashboard_data": dashboard_data,
            "dashboard_meta": dashboard_meta,
        },
    )


@router.post("/upload", status_code=status.HTTP_201_CREATED)
def upload_project_file(
    request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    token = request.cookies.get("access_token")
    user_id, _ = validate_user(token)
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    if user.role != "super_admin":
        permission = db.query(Permission).filter(Permission.user_id == user_id,
                                                 Permission.type == "manage dashboards").first()
        if not permission:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

    content = file.file.read(MAX_XER_UPLOAD_BYTES + 1)
    if len(content) > MAX_XER_UPLOAD_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"XER files must be no larger than {MAX_XER_UPLOAD_BYTES // (1024 * 1024)} MB",
        )

    header, tables = parse_xer(content)
    project = tables["PROJECT"][0]
    project_id = project.get("proj_id")
    root_wbs = next(
        (
            row
            for row in tables.get("PROJWBS", [])
            if row.get("proj_id") == project_id and row.get("proj_node_flag") == "Y"
        ),
        {},
    )
    try:
        export_date = date.fromisoformat(header["export_date"]) if header["export_date"] else None
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="XER export date is invalid",
        ) from exc

    table_counts = {name: len(rows) for name, rows in tables.items()}
    dashboard = Dashboard(
        filename=PurePath(file.filename.replace("\\", "/")).name if file.filename else None,
        uploaded_at=datetime.now(timezone.utc),
        xer_version=header["version"],
        export_date=export_date,
        export_type=header["export_type"],
        project_name=root_wbs.get("wbs_name") or project.get("proj_short_name"),
        export_user=header["export_user"],
        database_name=header["database_name"],
        currency=header["currency"],
        row_counts=table_counts,
        data={"header": header, "tables": tables},
    )

    try:
        db.add(dashboard)
        db.commit()
        db.refresh(dashboard)
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not save the XER import",
        ) from exc

    return {
        "id": dashboard.id,
        "project_name": dashboard.project_name,
        "filename": dashboard.filename,
        "uploaded_at": dashboard.uploaded_at.astimezone(ZoneInfo("Africa/Cairo")),
        "row_counts": dashboard.row_counts,
    }

@router.delete("/delete/{dashboard_id}")
def upload_project_file(request: Request, dashboard_id: int, db: Session = Depends(get_db)):
    token = request.cookies.get("access_token")
    user_id, _ = validate_user(token)
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    if user.role != "super_admin":
        permission = db.query(Permission).filter(Permission.user_id == user_id,
                                                 Permission.type == "manage dashboards").first()
        if not permission:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

    dashboard = db.query(Dashboard).filter(Dashboard.id == dashboard_id).first()
    if not dashboard:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    try:
        db.delete(dashboard)
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
    return {"success": True}


@router.patch("/add_notes/{dashboard_id}")
def add_notes(request: Request, payload: AddNotes, dashboard_id: int, db: Session = Depends(get_db)):
    token = request.cookies.get("access_token")
    user_id, _ = validate_user(token)
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    if user.role != "super_admin":
        permission = db.query(Permission).filter(Permission.user_id == user_id,
                                                 Permission.type == "manage dashboards").first()
        if not permission:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

    dashboard = db.query(Dashboard).filter(Dashboard.id == dashboard_id).first()
    if not dashboard:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    try:
        dashboard.notes = payload.text
        dashboard.last_edited = user_id
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

    return {"success": True}