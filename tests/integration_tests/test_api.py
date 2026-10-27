from sqlalchemy import select

from app.ad_platform import FakePlatform
from app.main import app, get_platform
from app.models import User

VALID_TEMPLATE = {
    "name": "promo",
    "settings": {"name": "x", "budget": 10, "geo": ["US"]},
}
USER = {"email": "a@gmail.com", "password": "secret123"}

def test_create_template(client):
    response = client.post("/templates", json=VALID_TEMPLATE)

    assert response.status_code == 201
    assert response.json()["name"] == "promo"
    assert "id" in response.json()


def test_negative_budget_is_rejected(client):
    bad = {
        "name": "promo",
        "settings": {"name": "x", "budget": -5, "geo": ["US"]},
    }
    response = client.post("/templates", json=bad)

    assert response.status_code == 422


def test_launch_flow(client):
    template_id = client.post("/templates", json=VALID_TEMPLATE).json()["id"]

    launch = client.post("/launches", json={"template_id": template_id, "count": 3})
    assert launch.status_code == 202
    job_id = launch.json()["id"]

    response = client.get(f"/launches/{job_id}")
    assert response.status_code == 200
    body = response.json()
    print(body)  # временно, ДО assert
    assert body["status"] == "done"
    assert len(body["items"]) == 3
    assert all(i["status"] == "created" for i in body["items"])


def test_platform_failure_marks_job_failed(client):
    app.dependency_overrides[get_platform] = lambda: FakePlatform(fail_rate=1.0)
    template_id = client.post("/templates", json=VALID_TEMPLATE).json()["id"]

    launch = client.post("/launches", json={"template_id": template_id, "count": 3})
    assert launch.status_code == 202
    job_id = launch.json()["id"]

    response = client.get(f"/launches/{job_id}")
    assert response.status_code == 200
    body = response.json()
    print(body)  # временно, ДО assert
    assert body["status"] == "failed"
    assert len(body["items"]) == 3
    assert all(i["status"] == "failed" for i in body["items"])


def test_launch_with_nonexistent_template(client):
    response = client.post("/launches", json={"template_id": 999, "count": 3})
    assert response.status_code == 404
    assert response.json()["detail"] == "Template not found"


def test_get_nonexistent_job(client):
    response = client.get("/launches/999")
    assert response.status_code == 404
    assert response.json()["detail"] == "Job not found"


def test_create_launch_with_invalid_count(client):
    template_id = client.post("/templates", json=VALID_TEMPLATE).json()["id"]
    response = client.post("/launches", json={"template_id": template_id, "count": -1})
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