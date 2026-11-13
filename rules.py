from datetime import datetime


def post_is_live(expires_at: datetime, now: datetime) -> bool:
    """Both arguments must be timezone-aware UTC timestamps."""
    return now < expires_at
