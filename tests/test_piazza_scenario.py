from datetime import datetime, timedelta, timezone
import rules


def future_expiry():
    return (
        datetime.now(timezone.utc)
        + timedelta(days=17)
    ).isoformat()


def test_tc_piazza_scenario(client, monkeypatch):

    users = {}

    # TC01: Register Olga, Nick, Mary and Nestor.
    # TC02: Log in each user and obtain their JWT.
    for name in ["olga", "nick", "mary", "nestor"]:

        credentials = {
            "email": f"{name}@example.com",
            "password": "test-password-123"
        }

        registered = client.post(
            "/auth/register",
            json=credentials
        )
        assert registered.status_code == 201

        logged_in = client.post(
            "/auth/login",
            json=credentials
        )
        assert logged_in.status_code == 200

        token = logged_in.json()["access_token"]

        users[name] = {
            "Authorization": f"Bearer {token}"
        }

    # TC03: Request without a token is rejected.
    response = client.get("/posts")
    assert response.status_code == 401

    # TC04, TC05, TC06: Olga, Nick & Mary create a Tech post each.
    posts = {}

    for name in ["olga", "nick", "mary"]:

        response = client.post(
            "/posts",
            json={
                "title": f"{name.title()}'s Tech post",
                "body": "Discussion about cloud computing",
                "topics": ["Tech"],
                "expires_at": future_expiry()
            },
            headers=users[name]
        )

        assert response.status_code == 201

        posts[name] = response.json()["id"]

    # TC07: Tech browsing returns three posts with no initial reactions or comments.
    response = client.get(
        "/posts?topic=Tech",
        headers=users["olga"]
    )

    assert response.status_code == 200
    assert len(response.json()) == 3

    for post in response.json():
        assert post["likes"] == 0
        assert post["dislikes"] == 0
        assert post["comments"] == []

    # Helper for sending a reaction.
    def react(user, post_id, value):
        response = client.put(
            f"/posts/{post_id}/reaction",
            json={"value": value},
            headers=users[user]
        )
        assert response.status_code == 200

    # TC08: Nick and Olga like Mary's post.
    react("nick", posts["mary"], "like")
    react("olga", posts["mary"], "like")

    # TC09: Nestor likes Nick's post and dislikes Mary's post.
    react("nestor", posts["nick"], "like")
    react("nestor", posts["mary"], "dislike")

    # TC10: check reaction counts.
    mary = client.get(
        f"/posts/{posts['mary']}",
        headers=users["olga"]
    ).json()

    nick = client.get(
        f"/posts/{posts['nick']}",
        headers=users["olga"]
    ).json()

    assert mary["likes"] == 2
    assert mary["dislikes"] == 1

    assert nick["likes"] == 1
    assert nick["dislikes"] == 0



    # TC11: Mary’s attempt to like her own post is rejected.
    response = client.put(
        f"/posts/{posts['mary']}/reaction",
        json={"value": "like"},
        headers=users["mary"]
    )
    assert response.status_code == 403

    # TC12: Nick and Olga each add at least two comments to Mary’s post.
    for name in ["nick", "olga"]:
        for number in [1, 2]:
            response = client.post(
                f"/posts/{posts['mary']}/comments",
                json={
                    "body": f"{name.title()} comment {number}"
                },
                headers=users[name]
            )
            assert response.status_code == 201

    # TC13: Browsing returns the correct reaction counts and comments.
    response = client.get(
        "/posts?topic=Tech",
        headers=users["olga"]
    )
    assert response.status_code == 200

    mary_post = next(
        post for post in response.json()
        if post["id"] == posts["mary"]
    )

    assert mary_post["likes"] == 2
    assert mary_post["dislikes"] == 1
    assert len(mary_post["comments"]) == 4

    comment_bodies = {
        comment["body"]
        for comment in mary_post["comments"]
    }

    assert comment_bodies == {
        "Nick comment 1",
        "Nick comment 2",
        "Olga comment 1",
        "Olga comment 2"
    }

    # TC14: Nestor creates a Health post.
    health_expiry = (
        datetime.now(timezone.utc)
        + timedelta(hours=1)
    )

    response = client.post(
        "/posts",
        json={
            "title": "Health discussion",
            "body": "How can we improve our health?",
            "topics": ["Health"],
            "expires_at": health_expiry.isoformat()
        },
        headers=users["nestor"]
    )

    assert response.status_code == 201
    health_id = response.json()["id"]

    # TC15: Health browsing returns the appropriate Health post.
    response = client.get(
        "/posts?topic=Health",
        headers=users["mary"]
    )

    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["id"] == health_id

    # TC16: Mary comments on Nestor’s live Health post.
    response = client.post(
        f"/posts/{health_id}/comments",
        json={"body": "A healthy diet is important."},
        headers=users["mary"]
    )
    assert response.status_code == 201

    # Change the application clock to the expiry time.
    monkeypatch.setattr(
        rules,
        "utcnow",
        lambda: health_expiry
    )

    # TC17: Mary’s attempted reaction after its expiry is rejected.
    response = client.put(
        f"/posts/{health_id}/reaction",
        json={"value": "like"},
        headers=users["mary"]
    )
    assert response.status_code == 409

    # TC18: The expired Health post remains readable with its existing comment.
    response = client.get(
        f"/posts/{health_id}",
        headers=users["mary"]
    )

    assert response.status_code == 200
    assert response.json()["status"] == "Expired"
    assert len(response.json()["comments"]) == 1
    assert response.json()["comments"][0]["body"] == (
        "A healthy diet is important."
    )

    # TC19: Expired-post browsing for Sport returns an empty list when none exist.
    response = client.get(
        "/posts?topic=Sport&status=Expired",
        headers=users["olga"]
    )

    assert response.status_code == 200
    assert response.json() == []

    # TC20: Mary’s post is the most-active Tech post while the relevant Tech posts remain live.
    response = client.get(
        "/topics/Tech/most-active",
        headers=users["olga"]
    )

    assert response.status_code == 200

    result = response.json()

    assert len(result) == 1
    assert result[0]["id"] == posts["mary"]
    assert result[0]["likes"] == 2
    assert result[0]["dislikes"] == 1
    assert result[0]["status"] == "Live"
