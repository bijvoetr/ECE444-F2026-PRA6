import pytest
import json
from pathlib import Path

from project.app import app, init_db

TEST_DB = "test.db"


@pytest.fixture
def client():
    BASE_DIR = Path(__file__).resolve().parent.parent
    app.config["TESTING"] = True
    app.config["DATABASE"] = BASE_DIR.joinpath(TEST_DB)

    init_db()
    yield app.test_client()
    init_db()


def login(client, username, password):
    return client.post(
        "/login",
        data=dict(username=username, password=password),
        follow_redirects=True,
    )


def logout(client):
    return client.get("/logout", follow_redirects=True)


def test_index(client):
    response = client.get("/", content_type="html/text")
    assert response.status_code == 200


def test_database(client):
    assert Path("test.db").is_file()


def test_empty_db(client):
    rv = client.get("/")
    assert b"No entries yet. Add some!" in rv.data


def test_login_logout(client):
    rv = login(client, app.config["USERNAME"], app.config["PASSWORD"])
    assert b"You were logged in" in rv.data

    rv = logout(client)
    assert b"You were logged out" in rv.data

    rv = login(client, app.config["USERNAME"] + "x", app.config["PASSWORD"])
    assert b"Invalid username" in rv.data

    rv = login(client, app.config["USERNAME"], app.config["PASSWORD"] + "x")
    assert b"Invalid password" in rv.data


def test_messages(client):
    login(client, app.config["USERNAME"], app.config["PASSWORD"])

    rv = client.post(
        "/add",
        data=dict(
            title="<Hello>",
            text="<strong>HTML</strong> allowed here",
        ),
        follow_redirects=True,
    )

    assert b"No entries yet. Add some!" not in rv.data

def test_delete_message(client):
    rv = client.get("/delete/1")
    data = json.loads(rv.data)

    assert data["status"] == 1