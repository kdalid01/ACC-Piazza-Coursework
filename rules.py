from datetime import datetime, timezone


def post_is_live(expires_at: datetime, now: datetime) -> bool:
    """Both arguments must be timezone-aware UTC timestamps."""
    return now < expires_at


def as_utc(value: datetime) -> datetime:
    # SQLite may return timestamps without timezone information.
    # Our database convention is to store these in UTC.
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)

    return value.astimezone(timezone.utc)


def post_status(expires_at: datetime, now: datetime) -> str:
    # Compare the two timestamps in UTC.
    expiry = as_utc(expires_at)
    current = as_utc(now)

    if current >= expiry:
        return "Expired"

    return "Live"