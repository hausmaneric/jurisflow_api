from source.app import app


def test_health_endpoint():
    client = app.test_client()
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["status"] is True
    assert payload["data"]["service"] == "JurisFlow API"


def test_routes_endpoint():
    client = app.test_client()
    response = client.get("/api/v1/routes")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["status"] is True
    assert any(route["path"] == "/api/v1/auth/login" for route in payload["data"])


def test_about_endpoint():
    client = app.test_client()
    response = client.get("/api/v1/about")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["status"] is True
    assert "auth" in payload["data"]["modules"]
