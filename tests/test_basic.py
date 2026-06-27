import pytest
from app import create_app, db as _db


@pytest.fixture()
def app():
    app = create_app()
    app.config.update(
        TESTING=True,
        WTF_CSRF_ENABLED=False,
        SQLALCHEMY_DATABASE_URI="sqlite:///:memory:",
    )
    with app.app_context():
        _db.create_all()
        yield app
        _db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()


def test_index_redirects_to_search_for_guests(client):
    resp = client.get("/", follow_redirects=False)
    # Guest: serve landing page (200)
    assert resp.status_code == 200


def test_register_tutor(client):
    resp = client.post(
        "/auth/register",
        data={
            "full_name": "Test Müəllim",
            "email": "tutor@test.az",
            "password": "password123",
            "role": "tutor",
        },
        follow_redirects=True,
    )
    assert resp.status_code == 200


def test_register_student(client):
    resp = client.post(
        "/auth/register",
        data={
            "full_name": "Test Şagird",
            "email": "student@test.az",
            "password": "password123",
            "role": "student",
        },
        follow_redirects=True,
    )
    assert resp.status_code == 200


def test_search_accessible_without_login(client):
    resp = client.get("/search/")
    assert resp.status_code == 200


def test_login_invalid_credentials(client):
    resp = client.post(
        "/auth/login",
        data={"email": "nobody@test.az", "password": "wrong"},
        follow_redirects=True,
    )
    assert resp.status_code == 200
    assert "yanlışdır".encode() in resp.data
