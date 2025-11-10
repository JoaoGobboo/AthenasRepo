import os

import pytest
from flask_jwt_extended import create_access_token

os.environ.setdefault("SECRET_KEY", "test-secret")


@pytest.fixture(scope="module")
def test_client(tmp_path_factory):
    db_dir = tmp_path_factory.mktemp("db")
    os.environ["DATABASE_URI"] = f"sqlite:///{db_dir}/test.db"

    from app import create_app
    from src.models import User
    from src.utils.db import session_scope

    app = create_app()
    client = app.test_client()

    with session_scope() as session:
        session.add(User(wallet_address="0xtest", is_admin=True))

    yield app, client


def test_healthcheck(test_client):
    app, client = test_client
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.get_json()["status"] == "ok"


def test_elections_requires_auth(test_client):
    app, client = test_client
    response = client.get("/api/v1/elections")
    assert response.status_code == 401


def test_create_election_flow(test_client):
    app, client = test_client
    with app.app_context():
        token = create_access_token(identity="0xtest")

    payload = {
        "title": "Presidencial 2024",
        "description": "Eleicao de teste",
        "candidates": ["Alice", "Bob"],
        "txHash": "0xtest",
    }
    response = client.post(
        "/api/v1/elections",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201
    body = response.get_json()
    assert body["election"]["title"] == payload["title"]
    assert len(body["election"]["candidates"]) == 2
