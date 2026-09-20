def test_404_html_for_browser(client):
    """Test that a browser requesting a non-existent URL gets the custom 404 HTML page."""
    response = client.get(
        "/unauthorized-secret-tunnel",
        headers={"Accept": "text/html,application/xhtml+xml"}
    )
    assert response.status_code == 404
    assert "FACILITY DEFENSE MONITOR" in response.text
    assert "404" in response.text
    assert "THREAT LEVEL: NOSY INTRUDER" in response.text


def test_404_json_for_api_client(client):
    """Test that an API client requesting JSON gets clean JSON response."""
    response = client.get(
        "/api/nonexistent-route",
        headers={"Accept": "application/json"}
    )
    assert response.status_code == 404
    assert response.headers["content-type"].startswith("application/json")
    data = response.json()
    assert "Sector not found" in data["detail"]


def test_404_preview_route(client):
    """Test direct /404 preview route."""
    response = client.get("/404")
    assert response.status_code == 404
    assert "FACILITY DEFENSE MONITOR" in response.text
