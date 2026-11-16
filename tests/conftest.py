import pytest

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from application import create_app
from database import get_db


@pytest.fixture
def app_factory(tmp_path):
    # Each test receives a different temporary directory and database.
    engine = create_engine(
        f"sqlite:///{tmp_path / 'test.db'}",
        connect_args={"check_same_thread": False},
    )

    sessions = sessionmaker(bind=engine)
    apps = []

    def make_app():
        app = create_app(engine)

        def override_db():
            with sessions() as session:
                yield session

        app.dependency_overrides[get_db] = override_db
        apps.append(app)

        return app

    yield make_app

    for app in apps:
        app.dependency_overrides.clear()

    engine.dispose()


@pytest.fixture
def client(app_factory):
    with TestClient(app_factory()) as test_client:
        yield test_client



@pytest.fixture
def auth_headers(client):
    # Register a user in the temporary test database.
    register_response = client.post(
        "/auth/register",
        json={
            "email": "test@example.com",
            "password": "test-password-123"
        }
    )

    assert register_response.status_code == 201

    # Log in using the registered credentials.
    login_response = client.post(
        "/auth/login",
        json={
            "email": "test@example.com",
            "password": "test-password-123"
        }
    )

    assert login_response.status_code == 200

    # Extract the JWT issued by Piazza.
    token = login_response.json()["access_token"]

    # Return a header that other tests can use.
    return {"Authorization": f"Bearer {token}"}



@pytest.fixture
def auth_headers(client):
    registered = client.post(
        "/auth/register",
        json={
            "email": "test@example.com",
            "password": "test-password-123"
        }
    )
    assert registered.status_code == 201

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
