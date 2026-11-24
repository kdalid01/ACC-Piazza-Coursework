from datetime import datetime, timedelta, timezone

import pytest
import models

from rules import post_is_live, post_status, as_utc


@pytest.mark.parametrize(
    "seconds, expected",
    [(-1, True), (0, False), (1, False)]
)
def test_post_is_live_boundary(seconds, expected):
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



def test_reaction_counts():
    # Create a post and reactions.
    post = models.Post(
        reactions=[
            models.Reaction(value="like"),
            models.Reaction(value="like"),
            models.Reaction(value="dislike")
        ]
    )

    assert post.likes == 2
    assert post.dislikes == 1

    # Change one reaction.
    post.reactions[0].value = "dislike"

    assert post.likes == 1
    assert post.dislikes == 2



def test_as_utc_conversion():
    # SQLite might return a timestamp without timezone info.
    naive = datetime(2027, 1, 1, 12, 0)

    converted = as_utc(naive)

    assert converted == datetime(
        2027, 1, 1, 12, 0,
        tzinfo=timezone.utc
    )

    # A UTC+2 timestamp should be converted to UTC.
    utc_plus_two = timezone(timedelta(hours=2))

    timestamp = datetime(
        2027, 1, 1, 14, 0,
        tzinfo=utc_plus_two
    )

    converted = as_utc(timestamp)

    assert converted == datetime(
        2027, 1, 1, 12, 0,
        tzinfo=timezone.utc
    )
    assert converted.utcoffset() == timedelta(0)
