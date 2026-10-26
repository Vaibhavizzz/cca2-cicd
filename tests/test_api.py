"""Integration tests for the Flask routes."""
import pytest

from app.main import app as flask_app


@pytest.fixture
def client():
    flask_app.config["TESTING"] = True
    with flask_app.test_client() as c:
        yield c


def test_health_returns_ok(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.get_json()["status"] == "ok"


def test_index_page_renders(client):
    response = client.get("/")
    assert response.status_code == 200
    assert b"Student Grade Management System" in response.data


def test_api_students_returns_all(client):
    response = client.get("/api/students")
    assert response.status_code == 200
    payload = response.get_json()
    assert isinstance(payload, list)
    assert len(payload) == 4
    assert "sgpa" in payload[0]


def test_api_single_student(client):
    response = client.get("/api/students/CS22001")
    assert response.status_code == 200
    assert response.get_json()["name"] == "Aarav Mehta"


def test_api_student_lookup_is_case_insensitive(client):
    assert client.get("/api/students/cs22001").status_code == 200


def test_api_unknown_student_returns_404(client):
    response = client.get("/api/students/NOPE999")
    assert response.status_code == 404
    assert "error" in response.get_json()


def test_grade_endpoint(client):
    payload = client.get("/api/grade/85").get_json()
    assert payload["grade"] == "A+"
    assert payload["points"] == 9
    assert payload["passed"] is True


def test_detail_page_renders(client):
    response = client.get("/student/CS22039")
    assert response.status_code == 200
    assert b"Meera Nair" in response.data


def test_unknown_detail_page_returns_404(client):
    assert client.get("/student/NOPE999").status_code == 404
