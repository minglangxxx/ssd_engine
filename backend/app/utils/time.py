from __future__ import annotations

from datetime import datetime, timedelta, timezone


BEIJING_TZ = timezone(timedelta(hours=8))

def beijing_now() -> datetime:
    return datetime.now(BEIJING_TZ)


def to_beijing_iso(dt: datetime | None, *, assume_utc: bool = False) -> str | None:
    if dt is None:
        return None

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc if assume_utc else BEIJING_TZ)

    return dt.astimezone(BEIJING_TZ).isoformat()