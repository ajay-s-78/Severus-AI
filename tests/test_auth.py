import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.database.database import create_tables, get_connection

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_db():
    create_tables()


def test_user_registration_success():
    username = f"user_{abs(hash('reg_test_1')) % 100000}"
    email = f"{username}@example.com"
    payload = {
        "username": username,
        "email": email,
        "password": "securepassword123"
    }
    response = client.post("/api/auth/register", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "access_token" in data
    assert data["user"]["username"] == username
    assert data["user"]["role"] == "user"


def test_user_registration_duplicate_user():
    username = f"user_{abs(hash('reg_dup_1')) % 100000}"
    email = f"{username}@example.com"
    payload = {
        "username": username,
        "email": email,
        "password": "securepassword123"
    }
    res1 = client.post("/api/auth/register", json=payload)
    assert res1.status_code == 200

    # Second attempt with same username/email
    res2 = client.post("/api/auth/register", json=payload)
    assert res2.status_code == 400
    assert "already registered" in res2.json()["detail"]


def test_user_login_success():
    username = f"user_{abs(hash('login_succ_1')) % 100000}"
    email = f"{username}@example.com"
    password = "mysecretpassword123"

    # Register
    client.post("/api/auth/register", json={"username": username, "email": email, "password": password})

    # Login
    login_res = client.post("/api/auth/login", json={"username": username, "password": password})
    assert login_res.status_code == 200
    data = login_res.json()
    assert data["status"] == "success"
    assert "access_token" in data
    assert data["user"]["username"] == username


def test_user_login_wrong_password():
    username = f"user_{abs(hash('login_wrong_1')) % 100000}"
    email = f"{username}@example.com"
    password = "correctpassword123"

    client.post("/api/auth/register", json={"username": username, "email": email, "password": password})

    login_res = client.post("/api/auth/login", json={"username": username, "password": "wrongpassword"})
    assert login_res.status_code == 401
    assert "Invalid username or password" in login_res.json()["detail"]


def test_protected_route_with_valid_token():
    username = f"user_{abs(hash('protected_1')) % 100000}"
    email = f"{username}@example.com"
    password = "password123"

    reg_res = client.post("/api/auth/register", json={"username": username, "email": email, "password": password})
    token = reg_res.json()["access_token"]

    me_res = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_res.status_code == 200
    data = me_res.json()
    assert data["status"] == "success"
    assert data["user"]["username"] == username


def test_protected_route_with_invalid_token():
    me_res = client.get("/api/auth/me", headers={"Authorization": "Bearer invalid_token_xyz"})
    assert me_res.status_code == 401


def test_logout_endpoint():
    res = client.post("/api/auth/logout")
    assert res.status_code == 200
    assert res.json()["status"] == "success"
