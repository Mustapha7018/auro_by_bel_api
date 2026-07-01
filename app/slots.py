"""Appointment slot availability — single source of truth used by both the
public slots endpoint and booking creation."""
from datetime import date

from .models import Availability


def js_weekday(d: date) -> int:
    """Python Mon=0..Sun=6 → JS Sun=0..Sat=6 (matches the front-ends)."""
    return (d.weekday() + 1) % 7


def is_open_day(av: Availability, d: date) -> bool:
    return js_weekday(d) in (av.working_days or []) and d.isoformat() not in (av.blocked_dates or [])


def day_slots(av: Availability, d: date, taken_times: set[str]) -> list[dict]:
    if not is_open_day(av, d):
        return []
    out = []
    for h in range(av.open_hour, av.close_hour):
        t = f"{h:02d}:00"
        out.append({"time": t, "available": t not in taken_times})
    return out
