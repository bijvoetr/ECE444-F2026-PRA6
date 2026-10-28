import pytest
import json
from pathlib import Path
from sqlalchemy import create_engine

from project.app import app, db

TEST_DB = "test.db"


@pytest.fixture
def client():
    BASE_DIR = Path(__file__).resolve().parent.parent

    app.config["TESTING"] = True

    app.config["DATABASE"] = BASE_DIR.joinpath(TEST_DB)

    app.config[
        "SQLALCHEMY_DATABASE_URI"
    ] = f"sqlite:///{BASE_DIR.joinpath(TEST_DB)}"

    with app.app_context():
        original_engine = db.engines[None]
        test_engine = create_engine("sqlite:///:memory:")
        db.engines[None] = test_engine
        try:
            db.create_all()
            yield app.test_client()
        finally:
            db.session.remove()
            db.drop_all()
            db.engines[None] = original_engine
            test_engine.dispose()


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

def test_search_page(client):
    rv = client.get("/search/")
    assert rv.status_code == 200

def test_delete_message(client):
    """Ensure the messages are being deleted"""

    rv = client.get("/delete/1")
    data = json.loads(rv.data)

    assert data["status"] == 0

    login(client, app.config["USERNAME"], app.config["PASSWORD"])

    rv = client.get("/delete/1")
    data = json.loads(rv.data)

    assert data["status"] == 1


def test_login_navigation_and_forms(client):
    from html.parser import HTMLParser

    class Forms(HTMLParser):
        def __init__(self):
            super().__init__()
            self.forms = []

        def handle_starttag(self, tag, attrs):
            if tag == "form":
                self.forms.append(dict(attrs))

    for path in ("/", "/search/"):
        assert b'href="/login"' in client.get(path).data
    parser = Forms()
    parser.feed(client.get("/login").get_data(as_text=True))
    assert {"action": "/login", "method": "post"} in parser.forms
    login(client, "admin", "admin")
    response = client.get("/")
    parser = Forms()
    parser.feed(response.get_data(as_text=True))
    assert {"action": "/add", "method": "post"} in parser.forms
    assert b'href="/logout"' in response.data
    assert b'href="/login"' not in response.data


def test_search_results(client):
    login(client, "admin", "admin")
    client.post("/add", data={"title": "First post", "text": "Needle"})
    client.post("/add", data={"title": "Other post", "text": "Unrelated"})
    response = client.get("/search/?query=NEEDLE")
    assert b"First post" in response.data
    assert b"Other post" not in response.data
    assert b"No matching entries." in client.get("/search/?query=missing").data
