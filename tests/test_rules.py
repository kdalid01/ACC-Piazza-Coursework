from datetime import datetime, timedelta, timezone

import pytest

from rules import post_is_live


@pytest.mark.parametrize(
    "seconds, expected",
    [(-1, True), (0, False), (1, False)]
)
def test_post_expiry_boundary(seconds, expected):
    expires_at = datetime(2026, 11, 1, 12, tzinfo=timezone.utc)
    now = expires_at + timedelta(seconds=seconds)

    assert post_is_live(expires_at, now) is expected
