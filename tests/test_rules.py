from datetime import datetime, timedelta, timezone

import pytest

from rules import post_is_live, post_status


@pytest.mark.parametrize(
    "seconds, expected",
    [(-1, True), (0, False), (1, False)]
)
def test_post_expiry_boundary(seconds, expected):
    expires_at = datetime(2026, 11, 1, 12, tzinfo=timezone.utc)
    now = expires_at + timedelta(seconds=seconds)

    assert post_is_live(expires_at, now) is expected


@pytest.mark.parametrize(
    "seconds, expected",
    [
        (-1, "Live"),
        (0, "Expired"),
        (1, "Expired"),
    ]
)
def test_post_expiry_boundary(seconds, expected):
    expiry = datetime(
        2027, 6, 1, 12, 0,
        tzinfo=timezone.utc
    )

    now = expiry + timedelta(seconds=seconds)

    assert post_status(expiry, now) == expected
