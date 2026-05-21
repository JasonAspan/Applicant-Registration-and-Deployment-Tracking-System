from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


try:
    PH_TIMEZONE = ZoneInfo("Asia/Manila")
except ZoneInfoNotFoundError:
    PH_TIMEZONE = timezone(timedelta(hours=8), name="Asia/Manila")


def ph_now():
    """Return current Philippine time as a naive datetime for existing DB columns."""
    return datetime.now(PH_TIMEZONE).replace(tzinfo=None)


def ph_iso(value):
    """Return an ISO string displayed in Philippine time for stored naive datetimes."""
    if not value:
        return None
    if value.tzinfo is not None:
        return value.astimezone(PH_TIMEZONE).replace(tzinfo=None).isoformat()
    return value.isoformat()
