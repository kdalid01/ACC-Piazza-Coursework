from datetime import datetime, timedelta, timezone
from fastapi.testclient import TestClient
import models
from database import get_db

import jwt
import rules
import pytest

from security import SECRET_KEY, ALGORITHM


def future_expiry():
    # Generate an expiry 17 days in the future.
    # This avoids using a fixed date that eventually becomes outdated.
    return (
        datetime.now(timezone.utc) + timedelta(days=17)
    ).isoformat()


def register_and_login(client):
    # Register a user in the test database.
    registered = client.post(
        "/auth/register",
        json={
            "email": "test@example.com",
            "password": "test-password-123"
        }
    )
    assert registered.status_code == 201

    # Login and obtain an access token.
    logged_in = client.post(
        "/auth/login",
        json={
            "email": "test@example.com",
            "password": "test-password-123"
        }
    )
    assert logged_in.status_code == 200

    token = logged_in.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}



def register_second_user(client):
    # Register a second user in the temporary test database.
    registered = client.post(
        "/auth/register",
        json={
            "email": "nick@example.com",
            "password": "test-password-123"
        }
    )

    assert registered.status_code == 201

    # Log in as the second user.
    logged_in = client.post(
        "/auth/login",
        json={
            "email": "nick@example.com",
            "password": "test-password-123"
        }
    )

    assert logged_in.status_code == 200

    token = logged_in.json()["access_token"]

    return {"Authorization": f"Bearer {token}"}



def test_starts_empty(client, auth_headers):
    response = client.get(
        "/posts",
        headers=auth_headers
    )

    assert response.status_code == 200
    assert response.json() == []



def test_create_and_retrieve(client, auth_headers):
    # Create a valid post with its required topic.
    post_data = {
        "title": "Cloud computing",
        "body": "What are the advantages of containers?",
        "topics": ["Tech"],
        "expires_at": future_expiry()
    }

    # Create a new post.
    created = client.post(
        "/posts", 
        json=post_data, 
        headers=auth_headers
    )

    # Check that the post was created successfully.
    assert created.status_code == 201

    # The server generates the ID, author and status.
    body = created.json()

    assert isinstance(body["id"], int)
    assert isinstance(body["author_id"], int)
    assert body["title"] == post_data["title"]
    assert body["body"] == post_data["body"]
    assert body["topics"] == ["Tech"]
    assert body["status"] == "Live"

    # Retrieve the post using its generated ID.
    post_id = body["id"]

    retrieved = client.get(
        f"/posts/{post_id}",
        headers=auth_headers
    )

    # Check that the request succeeded.
    assert retrieved.status_code == 200

    # Check that the retrieved data matches the created post.
    assert retrieved.json() == body


def test_missing_post(client, auth_headers):
    # A valid token allows us to test the missing-post case.
    response = client.get(
        "/posts/9999",
        headers=auth_headers
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Post not found"}



def test_data_survives_new_application(app_factory):
    post_data = {
        "title": "Cloud computing",
        "body": "What are the advantages of containers?",
        "topics": ["Tech"],
        "expires_at": future_expiry()
    }

    # Create a post using the first application instance.
    with TestClient(app_factory()) as first:
        headers = register_and_login(first)

        created = first.post(
            "/posts",
            json=post_data,
            headers=headers
        )

        assert created.status_code == 201
        body = created.json()

    # Create a second application instance using the same database.
    with TestClient(app_factory()) as restarted:
        # Login again. This also proves that the user was saved.
        login_response = restarted.post(
            "/auth/login",
            json={
                "email": "test@example.com",
                "password": "test-password-123"
            }
        )

        assert login_response.status_code == 200

        token = login_response.json()["access_token"]
        headers = {
            "Authorization": f"Bearer {token}"
        }

        response = restarted.get(
            f"/posts/{body['id']}",
            headers=headers
        )

        assert response.status_code == 200
        assert response.json() == body

    # Both application instances use the same temporary SQLite
    # database. The second application retrieves the data
    # created by the first application.



def test_health_does_not_require_authentication(client):
    # Health checks are publicly accessible.
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}



def test_repeated_and_switched_reactions(client, auth_headers):
    # Create a post as the first user.
    created = client.post(
        "/posts",
        json={
            "title": "Tech discussion",
            "body": "Is cloud computing useful?",
            "topics": ["Tech"],
            "expires_at": future_expiry()
        },
        headers=auth_headers
    )

    assert created.status_code == 201

    post_id = created.json()["id"]

    nick_headers = register_second_user(client)

    # First like.
    first = client.put(
        f"/posts/{post_id}/reaction",
        json={"value": "like"},
        headers=nick_headers
    )

    assert first.status_code == 200
    assert first.json()["likes"] == 1

    # Repeat the same like.
    repeated = client.put(
        f"/posts/{post_id}/reaction",
        json={"value": "like"},
        headers=nick_headers
    )

    assert repeated.status_code == 200
    assert repeated.json()["likes"] == 1
    assert repeated.json()["dislikes"] == 0

    # Switch the reaction from like to dislike.
    switched = client.put(
        f"/posts/{post_id}/reaction",
        json={"value": "dislike"},
        headers=nick_headers
    )

    assert switched.status_code == 200
    assert switched.json()["likes"] == 0
    assert switched.json()["dislikes"] == 1



def test_reaction_to_missing_post(client, auth_headers):
    response = client.put(
        "/posts/9999/reaction",
        json={"value": "like"},
        headers=auth_headers
    )

    assert response.status_code == 404




def test_invalid_reaction_value(client, auth_headers):
    # Create a live post.
    created = client.post(
        "/posts",
        json={
            "title": "Tech discussion",
            "body": "Testing reaction validation",
            "topics": ["Tech"],
            "expires_at": future_expiry()
        },
        headers=auth_headers
    )

    assert created.status_code == 201
    post_id = created.json()["id"]

    # Another user attempts an invalid reaction.
    nick_headers = register_second_user(client)

    response = client.put(
        f"/posts/{post_id}/reaction",
        json={"value": "love"},
        headers=nick_headers
    )

    assert response.status_code == 422




def test_user_can_comment_on_post(client, auth_headers):
    # Create a post as the logged-in user.
    created = client.post(
        "/posts",
        json={
            "title": "Cloud computing",
            "body": "What are containers?",
            "topics": ["Tech"],
            "expires_at": future_expiry()
        },
        headers=auth_headers
    )

    assert created.status_code == 201
    post_id = created.json()["id"]

    # The same user writes a comment.
    response = client.post(
        f"/posts/{post_id}/comments",
        json={"body": "Containers package applications."},
        headers=auth_headers
    )

    # Check that the comment was created.
    assert response.status_code == 201
    assert response.json()["body"] == "Containers package applications."
    assert response.json()["author_id"] == created.json()["author_id"]
    assert response.json()["post_id"] == post_id

    # Retrieve the post to confirm the comment was saved.
    retrieved = client.get(
        f"/posts/{post_id}",
        headers=auth_headers
    )

    assert retrieved.status_code == 200
    assert len(retrieved.json()["comments"]) == 1
    assert retrieved.json()["comments"][0]["body"] == (
        "Containers package applications."
    )



def test_empty_comment_rejected(client, auth_headers):
    created = client.post(
        "/posts",
        json={
            "title": "Discussion",
            "body": "Testing comment validation",
            "topics": ["Tech"],
            "expires_at": future_expiry()
        },
        headers=auth_headers
    )

    assert created.status_code == 201
    post_id = created.json()["id"]

    for text in ["", "   "]:
        response = client.post(
            f"/posts/{post_id}/comments",
            json={"body": text},
            headers=auth_headers
        )

        assert response.status_code == 422



def test_comment_on_missing_post(client, auth_headers):
    response = client.post(
        "/posts/9999/comments",
        json={"body": "Hello"},
        headers=auth_headers
    )

    assert response.status_code == 404
    assert response.json() == {
        "detail": "Post not found"
    }



def test_most_active_empty_topic(client, auth_headers):
    response = client.get(
        "/topics/Sport/most-active",
        headers=auth_headers
    )

    assert response.status_code == 200
    assert response.json() == []


def test_most_active_newest_post_wins(client, auth_headers):
    # Create two Tech posts.
    post_ids = []

    for title in ["Older post", "Newer post"]:
        created = client.post(
            "/posts",
            json={
                "title": title,
                "body": "Testing ranking ties",
                "topics": ["Tech"],
                "expires_at": future_expiry()
            },
            headers=auth_headers
        )

        assert created.status_code == 201
        post_ids.append(created.json()["id"])

    # Give both posts the same activity score.
    nick_headers = register_second_user(client)

    for post_id in post_ids:
        response = client.put(
            f"/posts/{post_id}/reaction",
            json={"value": "like"},
            headers=nick_headers
        )
        assert response.status_code == 200

    # Set distinct timestamps explicitly.
    db_override = client.app.dependency_overrides[get_db]
    db_generator = db_override()
    db = next(db_generator)

    try:
        older = db.get(models.Post, post_ids[0])
        newer = db.get(models.Post, post_ids[1])

        now = datetime.now(timezone.utc)

        older.created_at = (
            now - timedelta(hours=2)
        ).replace(tzinfo=None)

        newer.created_at = (
            now - timedelta(hours=1)
        ).replace(tzinfo=None)

        db.commit()
    finally:
        db_generator.close()

    # The newest post should win.
    response = client.get(
        "/topics/Tech/most-active",
        headers=auth_headers
    )

    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["id"] == post_ids[1]



def test_most_active_lowest_id_wins(client, auth_headers):
    post_ids = []

    for title in ["First post", "Second post"]:
        created = client.post(
            "/posts",
            json={
                "title": title,
                "body": "Testing identical timestamps",
                "topics": ["Tech"],
                "expires_at": future_expiry()
            },
            headers=auth_headers
        )

        assert created.status_code == 201
        post_ids.append(created.json()["id"])

    # Both posts have zero reactions.
    # Give them exactly the same creation timestamp.
    db_override = client.app.dependency_overrides[get_db]
    db_generator = db_override()
    db = next(db_generator)

    try:
        same_time = datetime(
            2026, 11, 1, 12, 0, 0
        )

        for post_id in post_ids:
            post = db.get(models.Post, post_id)
            post.created_at = same_time

        db.commit()
    finally:
        db_generator.close()

    response = client.get(
        "/topics/Tech/most-active",
        headers=auth_headers
    )

    assert response.status_code == 200
    assert len(response.json()) == 1

    # The first post has the lower ID.
    assert response.json()[0]["id"] == min(post_ids)



def test_most_active_excludes_expired_posts(
    client, auth_headers
):
    # Create two Tech posts.
    post_ids = []

    for title in ["Expired post", "Live post"]:
        created = client.post(
            "/posts",
            json={
                "title": title,
                "body": "Testing expiry in ranking",
                "topics": ["Tech"],
                "expires_at": future_expiry()
            },
            headers=auth_headers
        )

        assert created.status_code == 201
        post_ids.append(created.json()["id"])

    # Give the first post a reaction.
    nick_headers = register_second_user(client)

    reaction = client.put(
        f"/posts/{post_ids[0]}/reaction",
        json={"value": "like"},
        headers=nick_headers
    )

    assert reaction.status_code == 200

    # Make the first post expired.
    db_override = client.app.dependency_overrides[get_db]
    db_generator = db_override()
    db = next(db_generator)

    try:
        expired_post = db.get(models.Post, post_ids[0])

        expired_post.expires_at = (
            datetime.now(timezone.utc)
            - timedelta(seconds=1)
        ).replace(tzinfo=None)

        db.commit()
    finally:
        db_generator.close()

    # The second post must win despite having zero reactions.
    response = client.get(
        "/topics/Tech/most-active",
        headers=auth_headers
    )

    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["id"] == post_ids[1]



def test_duplicate_registration(client):
    user = {
        "email": "olga@example.com",
        "password": "secure-password-123"
    }

    # First registration succeeds.
    first = client.post("/auth/register", json=user)
    assert first.status_code == 201

    # Second registration with the same email fails.
    second = client.post("/auth/register", json=user)

    assert second.status_code == 409
    assert second.json()["detail"] == "Email already registered"


def test_incorrect_password(client):
    # Register a user.
    client.post(
        "/auth/register",
        json={
            "email": "olga@example.com",
            "password": "correct-password-123"
        }
    )

    # Attempt login with the wrong password.
    response = client.post(
        "/auth/login",
        json={
            "email": "olga@example.com",
            "password": "wrong-password-123"
        }
    )

    assert response.status_code == 401
    assert response.json()["detail"] == (
        "Invalid email or password"
    )


def test_invalid_token_rejected(client):
    # Supply a fabricated token.
    response = client.get(
        "/posts",
        headers={
            "Authorization": "Bearer this-is-not-a-valid-token"
        }
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid token"



def test_expired_token_rejected(client):
    # Create a JWT with an expiry time in the past.
    expired_time = (
        datetime.now(timezone.utc)
        - timedelta(minutes=5)
    )

    # Sign it using the application's test secret.
    expired_token = jwt.encode(
        {
            "sub": "olga@example.com",
            "exp": expired_time
        },
        SECRET_KEY,
        algorithm=ALGORITHM
    )

    # Attempt to access a protected endpoint.
    response = client.get(
        "/posts",
        headers={
            "Authorization": f"Bearer {expired_token}"
        }
    )

    # The expired JWT must be rejected.
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid token"



def test_exact_expiry_boundary(
    client, auth_headers, monkeypatch
):
    # Choose a fixed time instead of the real clock.
    start = datetime(
        2027, 1, 1, 12, 0,
        tzinfo=timezone.utc
    )
    expiry = start + timedelta(hours=1)

    # Make the application believe it is 12:00.
    monkeypatch.setattr(
        rules, "utcnow", lambda: start
    )

    # Create a post that expires at 13:00.
    created = client.post(
        "/posts",
        json={
            "title": "Expiry boundary test",
            "body": "Testing the exact expiry time",
            "topics": ["Tech"],
            "expires_at": expiry.isoformat()
        },
        headers=auth_headers
    )

    assert created.status_code == 201
    post_id = created.json()["id"]
    assert created.json()["status"] == "Live"

    # Register a second user who can react.
    nick_headers = register_second_user(client)

    # Move the clock to one second before expiry.
    monkeypatch.setattr(
        rules,
        "utcnow",
        lambda: expiry - timedelta(seconds=1)
    )

    # A reaction is allowed just before expiry.
    reaction = client.put(
        f"/posts/{post_id}/reaction",
        json={"value": "like"},
        headers=nick_headers
    )

    assert reaction.status_code == 200
    assert reaction.json()["likes"] == 1

    # Move the clock to EXACTLY the expiry time.
    monkeypatch.setattr(
        rules, "utcnow", lambda: expiry
    )

    # The same reaction must now be rejected.
    reaction = client.put(
        f"/posts/{post_id}/reaction",
        json={"value": "like"},
        headers=nick_headers
    )

    assert reaction.status_code == 409

    # Comments must also be rejected.
    comment = client.post(
        f"/posts/{post_id}/comments",
        json={"body": "Too late"},
        headers=nick_headers
    )

    assert comment.status_code == 409

    # The expired post must remain readable.
    retrieved = client.get(
        f"/posts/{post_id}",
        headers=auth_headers
    )

    assert retrieved.status_code == 200
    assert retrieved.json()["status"] == "Expired"
    assert retrieved.json()["likes"] == 1
    assert retrieved.json()["comments"] == []


    # Move the clock to one second after expiry.
    monkeypatch.setattr(
        rules,
        "utcnow",
        lambda: expiry + timedelta(seconds=1)
    )

    # The post should still be expired.
    retrieved = client.get(
        f"/posts/{post_id}",
        headers=auth_headers
    )

    assert retrieved.status_code == 200
    assert retrieved.json()["status"] == "Expired"

    # A new comment should be rejected after expiry.
    comment = client.post(
        f"/posts/{post_id}/comments",
        json={"body": "Comment after expiry"},
        headers=nick_headers
    )

    assert comment.status_code == 409

    # A repeated reaction should be rejected after expiry.
    reaction = client.put(
        f"/posts/{post_id}/reaction",
        json={"value": "like"},
        headers=nick_headers
    )

    assert reaction.status_code == 409



def test_post_with_multiple_topics(client, auth_headers):
    # Create one post belonging to two topics.
    response = client.post(
        "/posts",
        json={
            "title": "Technology and health",
            "body": "How can technology improve healthcare?",
            "topics": ["Tech", "Health"],
            "expires_at": future_expiry()
        },
        headers=auth_headers
    )

    assert response.status_code == 201

    post_id = response.json()["id"]

    # The same post should appear under Tech.
    tech = client.get(
        "/posts?topic=Tech",
        headers=auth_headers
    )

    assert tech.status_code == 200
    assert len(tech.json()) == 1
    assert tech.json()[0]["id"] == post_id


    # The same post should also appear under Health.
    health = client.get(
        "/posts?topic=Health",
        headers=auth_headers
    )

    assert health.status_code == 200
    assert len(health.json()) == 1
    assert health.json()[0]["id"] == post_id

    # But not under Sport.
    sport = client.get(
        "/posts?topic=Sport",
        headers=auth_headers
    )

    assert sport.status_code == 200
    assert sport.json() == []



def test_invalid_topic_rejected(client, auth_headers):
    # Parenting is not one of the four permitted topics.
    response = client.get(
        "/posts?topic=Parenting",
        headers=auth_headers
    )

    assert response.status_code == 422


def test_invalid_status_filter_rejected(client, auth_headers):
    # Pending is not a permitted post status.
    response = client.get(
        "/posts?status=Pending",
        headers=auth_headers
    )

    assert response.status_code == 422


def test_expiry_without_timezone_rejected(client, auth_headers):
    # This timestamp has no Z or UTC offset.
    response = client.post(
        "/posts",
        json={
            "title": "Timezone check",
            "body": "Testing an invalid expiry timestamp",
            "topics": ["Tech"],
            "expires_at": "2027-06-01T12:00:00"
        },
        headers=auth_headers
    )

    assert response.status_code == 422



def test_most_active_with_zero_reactions(client, auth_headers):
    # Create one Tech post without any reactions.
    created = client.post(
        "/posts",
        json={
            "title": "Cloud computing discussion",
            "body": "What are the benefits of cloud computing?",
            "topics": ["Tech"],
            "expires_at": future_expiry()
        },
        headers=auth_headers
    )

    assert created.status_code == 201
    post_id = created.json()["id"]

    # The post should be the most active even with zero reactions.
    response = client.get(
        "/topics/Tech/most-active",
        headers=auth_headers
    )

    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["id"] == post_id
    assert response.json()[0]["likes"] == 0
    assert response.json()[0]["dislikes"] == 0
    assert response.json()[0]["status"] == "Live"



def test_combined_topic_and_status_filter(
    client, auth_headers, monkeypatch
):
    # Using a fixed time so the test doesn't depend on the real clock.
    start = datetime(
        2027, 1, 1, 12, 0,
        tzinfo=timezone.utc
    )

    monkeypatch.setattr(
        rules, "utcnow", lambda: start
    )

    # Create three posts with different topics and expiry times.
    test_posts = [
        ("Live Tech post", "Tech", timedelta(days=17)),
        ("Expired Tech post", "Tech", timedelta(hours=1)),
        ("Live Health post", "Health", timedelta(days=17)),
    ]

    post_ids = {}

    for title, topic, duration in test_posts:
        response = client.post(
            "/posts",
            json={
                "title": title,
                "body": "Testing topic and status filtering",
                "topics": [topic],
                "expires_at": (start + duration).isoformat()
            },
            headers=auth_headers
        )

        assert response.status_code == 201
        post_ids[title] = response.json()["id"]

    # Moving the clock forward by two hours.
    # The second Tech post should now be expired.
    monkeypatch.setattr(
        rules,
        "utcnow",
        lambda: start + timedelta(hours=2)
    )

    # Filter for live Tech posts.
    response = client.get(
        "/posts?topic=Tech&status=Live",
        headers=auth_headers
    )

    assert response.status_code == 200
    assert [post["id"] for post in response.json()] == [
        post_ids["Live Tech post"]
    ]

    # Filter for expired Tech posts.
    response = client.get(
        "/posts?topic=Tech&status=Expired",
        headers=auth_headers
    )

    assert response.status_code == 200
    assert [post["id"] for post in response.json()] == [
        post_ids["Expired Tech post"]
    ]

    # Without a status filter, both Tech posts should be visible.
    response = client.get(
        "/posts?topic=Tech",
        headers=auth_headers
    )

    assert response.status_code == 200
    assert {post["id"] for post in response.json()} == {
        post_ids["Live Tech post"],
        post_ids["Expired Tech post"]
    }

    # Without any filters, all three posts should be visible.
    response = client.get(
        "/posts",
        headers=auth_headers
    )

    assert response.status_code == 200
    assert len(response.json()) == 3




@pytest.mark.parametrize(
    "changes",
    [
        {"title": ""},
        {"title": "   "},
        {"body": ""},
        {"body": "   "},
        {"topics": []},
        {"topics": ["Parenting"]},
    ]
)
def test_invalid_post_fields(client, auth_headers, changes):
    # Start with a valid post.
    post_data = {
        "title": "Tech discussion",
        "body": "A question about technology",
        "topics": ["Tech"],
        "expires_at": future_expiry()
    }

    # Replace one valid field with an invalid value.
    post_data.update(changes)

    response = client.post(
        "/posts",
        json=post_data,
        headers=auth_headers
    )

    assert response.status_code == 422


def test_post_expiry_in_past_rejected(client, auth_headers):
    past_expiry = (
        datetime.now(timezone.utc)
        - timedelta(days=1)
    ).isoformat()

    response = client.post(
        "/posts",
        json={
            "title": "Expired before creation",
            "body": "This post should not be accepted",
            "topics": ["Tech"],
            "expires_at": past_expiry
        },
        headers=auth_headers
    )

    assert response.status_code == 422



@pytest.mark.parametrize(
    "method, path, body",
    [
        ("get", "/posts", None),
        ("get", "/posts/1", None),
        ("post", "/posts", {
            "title": "Test post",
            "body": "Test body",
            "topics": ["Tech"],
            "expires_at": "2027-06-01T12:00:00Z"
        }),
        ("put", "/posts/1/reaction", {"value": "like"}),
        ("post", "/posts/1/comments", {"body": "Test comment"}),
        ("get", "/topics/Tech/most-active", None),
    ]
)
def test_business_endpoints_require_authentication(
    client, method, path, body
):
    response = client.request(
        method.upper(),
        path,
        json=body
    )

    assert response.status_code == 401

