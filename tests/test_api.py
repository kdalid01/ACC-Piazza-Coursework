from datetime import datetime, timedelta, timezone
from fastapi.testclient import TestClient
import models
from database import get_db

import jwt
from security import SECRET_KEY, ALGORITHM


def future_expiry():
    # Generate an expiry one day in the future.
    # This avoids using a fixed date that eventually becomes outdated.
    return (
        datetime.now(timezone.utc) + timedelta(days=1)
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



def test_invalid_post(client, auth_headers):
    # The title is invalid, but the other fields are valid.
    # This isolates title validation.
    post_data = {
        "title": "",
        "body": "This post has an empty title.",
        "topics": ["Tech"],
        "expires_at": future_expiry()
    }

    response = client.post(
        "/posts",
        json=post_data,
        headers=auth_headers
    )

    assert response.status_code == 422



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


def test_posts_require_authentication(client):
    # A request without a JWT must be rejected.
    response = client.get("/posts")

    assert response.status_code == 401


def test_health_does_not_require_authentication(client):
    # Health checks are publicly accessible.
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}



def test_user_can_like_another_users_post(client, auth_headers):
    # Create a post as the first user.
    post_data = {
        "title": "Cloud computing",
        "body": "What are the advantages of containers?",
        "topics": ["Tech"],
        "expires_at": future_expiry()
    }

    created = client.post(
        "/posts",
        json=post_data,
        headers=auth_headers
    )

    assert created.status_code == 201

    post_id = created.json()["id"]

    # Register and log in as a different user.
    nick_headers = register_second_user(client)

    # Nick likes the first user's post.
    response = client.put(
        f"/posts/{post_id}/reaction",
        json={"value": "like"},
        headers=nick_headers
    )

    print("Reaction response:", response.status_code, response.json())

    assert response.status_code == 200

    assert response.json() == {
        "post_id": post_id,
        "likes": 1,
        "dislikes": 0
    }


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


def test_author_cannot_react_to_own_post(client, auth_headers):
    # Create a post as the first user.
    created = client.post(
        "/posts",
        json={
            "title": "My Tech post",
            "body": "Discussion about cloud computing",
            "topics": ["Tech"],
            "expires_at": future_expiry()
        },
        headers=auth_headers
    )

    assert created.status_code == 201
    post_id = created.json()["id"]

    # The same user attempts to like their own post.
    response = client.put(
        f"/posts/{post_id}/reaction",
        json={"value": "like"},
        headers=auth_headers
    )

    assert response.status_code == 403


def test_reaction_requires_authentication(client):
    response = client.put(
        "/posts/9999/reaction",
        json={"value": "like"}
    )

    assert response.status_code == 401



def test_reaction_to_missing_post(client, auth_headers):
    response = client.put(
        "/posts/9999/reaction",
        json={"value": "like"},
        headers=auth_headers
    )

    assert response.status_code == 404



def test_invalid_reaction_value(client, auth_headers):
    response = client.put(
        "/posts/9999/reaction",
        json={"value": "love"},
        headers=auth_headers
    )

    assert response.status_code == 422



def test_expired_post_rejects_reaction(client, auth_headers):
    # Create a live post.
    created = client.post(
        "/posts",
        json={
            "title": "Expiring Tech post",
            "body": "Discussion before expiry",
            "topics": ["Tech"],
            "expires_at": future_expiry()
        },
        headers=auth_headers
    )

    assert created.status_code == 201
    post_id = created.json()["id"]

    # A different user will attempt the reaction.
    nick_headers = register_second_user(client)

    # Access the same temporary test database.
    db_override = client.app.dependency_overrides[get_db]
    db_generator = db_override()
    db = next(db_generator)

    try:
        post = db.query(models.Post).filter(
            models.Post.id == post_id
        ).first()

        assert post is not None

        # Simulate the post having expired.
        post.expires_at = (
            datetime.now(timezone.utc)
            - timedelta(seconds=1)
        ).replace(tzinfo=None)

        db.commit()

    finally:
        db_generator.close()

    # Nick attempts to react after expiry.
    response = client.put(
        f"/posts/{post_id}/reaction",
        json={"value": "like"},
        headers=nick_headers
    )

    assert response.status_code == 409


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



def test_multiple_comments_on_post(client, auth_headers):
    # Create a live post.
    created = client.post(
        "/posts",
        json={
            "title": "Cloud discussion",
            "body": "What do you think about cloud computing?",
            "topics": ["Tech"],
            "expires_at": future_expiry()
        },
        headers=auth_headers
    )

    assert created.status_code == 201
    post_id = created.json()["id"]

    # Add two different comments.
    for text in ["First comment", "Second comment"]:
        response = client.post(
            f"/posts/{post_id}/comments",
            json={"body": text},
            headers=auth_headers
        )
        assert response.status_code == 201

    # Retrieve the post and check both comments.
    retrieved = client.get(
        f"/posts/{post_id}",
        headers=auth_headers
    )

    assert retrieved.status_code == 200

    comments = retrieved.json()["comments"]
    assert len(comments) == 2
    assert {comment["body"] for comment in comments} == {
        "First comment",
        "Second comment"
    }



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



def test_expired_post_rejects_comment(client, auth_headers):
    # Create a live post.
    created = client.post(
        "/posts",
        json={
            "title": "Expiring discussion",
            "body": "This discussion will expire.",
            "topics": ["Health"],
            "expires_at": future_expiry()
        },
        headers=auth_headers
    )

    assert created.status_code == 201
    post_id = created.json()["id"]

    # Add a comment while the post is live.
    comment = client.post(
        f"/posts/{post_id}/comments",
        json={"body": "Comment before expiry"},
        headers=auth_headers
    )

    assert comment.status_code == 201

    # Access the temporary test database.
    db_override = client.app.dependency_overrides[get_db]
    db_generator = db_override()
    db = next(db_generator)

    try:
        # Find the post in SQLite.
        post = db.query(models.Post).filter(
            models.Post.id == post_id
        ).first()

        assert post is not None

        # Simulate the post having expired.
        post.expires_at = (
            datetime.now(timezone.utc)
            - timedelta(seconds=1)
        ).replace(tzinfo=None)

        db.commit()
    finally:
        db_generator.close()

    # Attempt to comment after expiry.
    rejected = client.post(
        f"/posts/{post_id}/comments",
        json={"body": "Comment after expiry"},
        headers=auth_headers
    )

    assert rejected.status_code == 409

    # The expired post must still be readable.
    retrieved = client.get(
        f"/posts/{post_id}",
        headers=auth_headers
    )

    assert retrieved.status_code == 200
    assert retrieved.json()["status"] == "Expired"

    # Its original comment must still exist.
    comments = retrieved.json()["comments"]

    assert len(comments) == 1
    assert comments[0]["body"] == "Comment before expiry"



def test_most_active_post(client, auth_headers):
    # Create three Tech posts as the first user.
    post_ids = []

    for title in ["Post A", "Post B", "Post C"]:
        created = client.post(
            "/posts",
            json={
                "title": title,
                "body": "Testing post activity",
                "topics": ["Tech"],
                "expires_at": future_expiry()
            },
            headers=auth_headers
        )

        assert created.status_code == 201
        post_ids.append(created.json()["id"])

    # Create a second user who can react to the posts.
    nick_headers = register_second_user(client)

    # Nick likes Post A.
    response = client.put(
        f"/posts/{post_ids[0]}/reaction",
        json={"value": "like"},
        headers=nick_headers
    )
    assert response.status_code == 200

    # Nick dislikes Post B.
    response = client.put(
        f"/posts/{post_ids[1]}/reaction",
        json={"value": "dislike"},
        headers=nick_headers
    )
    assert response.status_code == 200

    # Nick has not reacted to Post C.
    # A and B therefore have one reaction each.
    # C has zero reactions.

    response = client.get(
        "/topics/Tech/most-active",
        headers=auth_headers
    )

    assert response.status_code == 200

    result = response.json()

    # Post B is newer than Post A, so it wins the tie.
    assert len(result) == 1
    assert result[0]["id"] == post_ids[1]
    assert result[0]["likes"] == 0
    assert result[0]["dislikes"] == 1


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
