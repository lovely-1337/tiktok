import secrets
from datetime import datetime, timedelta, timezone
from sqlalchemy import select

from app.ad_platform import FakePlatform
from app.main import app, get_platform
from app.models import User, TikTokOAuthState

VALID_TEMPLATE = {
    "name": "promo",
    "settings": {"name": "x", "budget": 10, "geo": ["US"]},
}
USER = {"email": "a@gmail.com", "password": "secret123"}
user_a = {"email": "a@example.com", "password": "secret123"}
user_b = {"email": "b@example.com", "password": "secret123"}

def get_auth_headers(client):
    client.post("/register", json=USER)
    login_response = client.post("/login", json=USER)
    token = login_response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

def get_auth_headers_dry_a(client):
    client.post("/register", json=user_a)
    login_response = client.post("/login", json=user_a)
    token = login_response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

def get_auth_headers_dry_b(client):
    client.post("/register", json=user_b)
    login_response = client.post("/login", json=user_b)
    token = login_response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_create_template(client):
    headers = get_auth_headers(client)

    response = client.post(
        "/templates",
        json=VALID_TEMPLATE,
        headers=headers,
    )
    

    assert response.status_code == 201
    assert response.json()["name"] == "promo"
    assert "id" in response.json()

def test_cant_see_another_users_job_a(client):
    header_a = get_auth_headers_dry_a(client)
    
    response = client.post(
        "/templates",
        json=VALID_TEMPLATE,
        headers=header_a,
    )
    template_id = response.json()["id"]
    res = client.post("/launches", json={"template_id": template_id, "count": 3}, headers=header_a)
    id = res.json()["id"]
    header_b = get_auth_headers_dry_b(client)
    err = client.get(f"/launches/{id}", headers=header_b)

    assert err.status_code == 404

def test_cant_see_another_users_job_b(client):
    header_b = get_auth_headers_dry_b(client)
    response = client.post(
        "/templates",
        json=VALID_TEMPLATE,
        headers=header_b,
    )
    template_id = response.json()["id"]
    res = client.post("/launches", json={"template_id": template_id, "count": 3}, headers=header_b)
    id = res.json()["id"]
    header_a = get_auth_headers_dry_a(client)
    err = client.get(f"/launches/{id}", headers=header_a)

    assert err.status_code == 404

def test_negative_budget_is_rejected(client):
    headers = get_auth_headers(client)
    bad = {
        "name": "promo",
        "settings": {"name": "x", "budget": -5, "geo": ["US"]},
    }
    response = client.post("/templates", json=bad, headers=headers)

    assert response.status_code == 422


def test_launch_flow(client):
    headers = get_auth_headers(client)
    template_id = client.post("/templates", json=VALID_TEMPLATE, headers=headers).json()["id"]

    launch = client.post("/launches", json={"template_id": template_id, "count": 3}, headers=headers)
    assert launch.status_code == 202
    job_id = launch.json()["id"]

    response = client.get(f"/launches/{job_id}", headers=headers)
    assert response.status_code == 200
    body = response.json()
    print(body)  # временно, ДО assert
    assert body["status"] == "done"
    assert len(body["items"]) == 3
    assert all(i["status"] == "created" for i in body["items"])


def test_platform_failure_marks_job_failed(client):
    headers = get_auth_headers(client)
    app.dependency_overrides[get_platform] = lambda: FakePlatform(fail_rate=1.0)
    template_id = client.post("/templates", json=VALID_TEMPLATE, headers=headers).json()["id"]

    launch = client.post("/launches", json={"template_id": template_id, "count": 3}, headers=headers)
    assert launch.status_code == 202
    job_id = launch.json()["id"]

    response = client.get(f"/launches/{job_id}", headers=headers)
    assert response.status_code == 200
    body = response.json()
    print(body)  # временно, ДО assert
    assert body["status"] == "failed"
    assert len(body["items"]) == 3
    assert all(i["status"] == "failed" for i in body["items"])


def test_launch_with_nonexistent_template(client):
    headers = get_auth_headers(client)
    response = client.post("/launches", json={"template_id": 999, "count": 3}, headers=headers)
    assert response.status_code == 404
    assert response.json()["detail"] == "Template not found"


def test_get_nonexistent_job(client):
    headers = get_auth_headers(client)
    response = client.get("/launches/999", headers=headers)
    assert response.status_code == 404
    assert response.json()["detail"] == "Job not found"


def test_create_launch_with_invalid_count(client):
    headers = get_auth_headers(client)
    template_id = client.post("/templates", json=VALID_TEMPLATE, headers=headers).json()["id"]
    response = client.post("/launches", json={"template_id": template_id, "count": -1}, headers=headers)
    assert response.status_code == 422


def test_register_success(client):
    response = client.post("/register", json=USER)

    assert response.status_code == 201
    body = response.json()
    assert body["email"] == "a@gmail.com"
    assert "id" in body
    assert "password_hash" not in body
    assert "password" not in body


def test_register_duplicate_email(client):
    client.post("/register", json=USER)
    response = client.post("/register", json=USER)

    assert response.status_code == 409


def test_register_duplicate_email_other_case(client):
    client.post("/register", json=USER)
    response = client.post(
        "/register", json={"email": "A@Gmail.com", "password": "secret123"}
    )

    assert response.status_code == 409


def test_register_short_password(client):
    response = client.post(
        "/register", json={"email": "a@gmail.com", "password": "short"}
    )

    assert response.status_code == 422


def test_register_invalid_email(client):
    response = client.post(
        "/register", json={"email": "not-an-email", "password": "secret123"}
    )

    assert response.status_code == 422

def test_password_is_stored_hashed(client, session):
    client.post("/register", json=USER)

    user = session.scalars(select(User)).one()
    assert user.password_hash != "secret123"
    assert user.password_hash.startswith("$argon2")

def test_login(client):
    client.post("/register", json=USER)

    response = client.post("/login", json=USER)

    assert response.status_code == 200
    body = response.json()
    assert body["access_token"]
    assert body["token_type"] == "bearer"

def test_login_incorrect_password(client):
    client.post("/register", json=USER)

    response = client.post("/login", json = {
        "email": "a@gmail.com", "password": "secret124"
    })

    assert response.status_code == 401
def test_login_nonexistent_email(client):
    response = client.post(
        "/login",
        json={"email": "nobody@gmail.com", "password": "secret123"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Incorrect email or password"

def test_user_see_his_task(client):
    client.post("/register", json=USER)

    login_response = client.post("/login", json=USER)
    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    template_response = client.post(
        "/templates", json=VALID_TEMPLATE, headers=headers
    )
    template_id = template_response.json()["id"]

    launch_response = client.post(
        "/launches",
        json={"template_id": template_id, "count": 1},
        headers=headers,
    )
    job_id = launch_response.json()["id"]

    response = client.get(f"/launches/{job_id}", headers=headers)
    assert response.status_code == 200



def test_tiktok_callback_state_is_one_time(client):
    headers = get_auth_headers(client)

    start = client.get("/auth/tiktok/start", headers=headers)
    assert start.status_code == 200
    state_value = start.json()["state"]

    params = {"state": state_value, "auth_code": "fake-code"}
    first = client.get("/auth/tiktok/callback", params=params)
    second = client.get("/auth/tiktok/callback", params=params)

    assert first.status_code == 200
    assert second.status_code == 400

def test_tiktok_state_is_expired(client, session):
    get_auth_headers(client)  # регистрирует пользователя

    user = session.scalar(
        select(User).where(User.email == USER["email"])
    )
    state_value = secrets.token_urlsafe(32)

    oauth_state = TikTokOAuthState(
        user_id=user.id,
        state=state_value,
        expires_at=datetime.now(timezone.utc) - timedelta(seconds=1),
    )
    session.add(oauth_state)
    session.commit()

    response = client.get(
        "/auth/tiktok/callback",
        params={"state": state_value, "auth_code": "fake-code"},
    )

    assert response.status_code == 400