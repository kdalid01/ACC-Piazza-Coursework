from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient


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
 