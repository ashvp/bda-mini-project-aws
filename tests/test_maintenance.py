import io
import pytest


@pytest.fixture
def resident_token(client):
    # Register and log in a resident
    client.post("/auth/register", json={
        "username": "alice",
        "password": "Password123!",
        "apartment_block_num": "Tower 1",
        "house_num": "501"
    })
    resp = client.post("/auth/login", json={
        "username": "alice",
        "password": "Password123!"
    })
    return resp.json()["access_token"]


def test_upload_maintenance_request(client, resident_token):
    """Test resident uploading a problem with an image."""
    fake_image = io.BytesIO(b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00`\x00`\x00\x00")
    files = {"image": ("leakage.jpg", fake_image, "image/jpeg")}
    data = {
        "problem_category": "Plumbing",
        "details": "Major water leakage under the kitchen sink"
    }

    response = client.post(
        "/maintenance",
        data=data,
        files=files,
        headers={"Authorization": f"Bearer {resident_token}"}
    )

    assert response.status_code == 201
    result = response.json()
    assert result["maintanance_id"] is not None
    assert result["problem_category"] == "Plumbing"
    assert result["details"] == "Major water leakage under the kitchen sink"
    assert "leakage" in result["image_url"] or "/uploads/" in result["image_url"] or "s3" in result["image_url"]
    assert result["isAssignedTo"] is None
    assert result["house"]["house_num"] == "501"


def test_upload_invalid_file_extension(client, resident_token):
    """Test rejecting files that are not valid images."""
    bad_file = io.BytesIO(b"malicious script content")
    files = {"image": ("script.exe", bad_file, "application/octet-stream")}
    data = {
        "problem_category": "Electrical",
        "details": "AC thermostat not turning on"
    }

    response = client.post(
        "/maintenance",
        data=data,
        files=files,
        headers={"Authorization": f"Bearer {resident_token}"}
    )

    assert response.status_code == 400
    assert "Invalid file extension" in response.json()["detail"]


def test_get_my_maintenance_requests(client, resident_token):
    """Test retrieving all tickets filed by the logged-in user."""
    response = client.get(
        "/maintenance/my",
        headers={"Authorization": f"Bearer {resident_token}"}
    )
    assert response.status_code == 200
    tickets = response.json()
    assert len(tickets) >= 1
    assert tickets[0]["problem_category"] == "Plumbing"


def test_unauthenticated_request_rejected(client):
    """Test unauthenticated maintenance creation fails."""
    fake_image = io.BytesIO(b"fake data")
    files = {"image": ("test.png", fake_image, "image/png")}
    response = client.post(
        "/maintenance",
        data={"problem_category": "HVAC", "details": "AC not cooling"},
        files=files
    )
    assert response.status_code == 401
