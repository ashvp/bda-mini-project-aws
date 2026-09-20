import pytest


def test_admin_login(client):
    """Test unified login with pre-seeded admin credentials."""
    response = client.post(
        "/auth/login",
        json={"username": "admin", "password": "AdminSecurePassword123!"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["username"] == "admin"
    assert data["user"]["isAdmin"] is True


def test_user_registration(client):
    """Test resident user registration with house and block details."""
    payload = {
        "username": "john_doe",
        "password": "Password123!",
        "apartment_block_num": "Block B",
        "house_num": "204"
    }
    response = client.post("/auth/register", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["username"] == "john_doe"
    assert data["isAdmin"] is False
    assert data["houseid"] is not None
    assert data["house"]["apartment_block_num"] == "Block B"
    assert data["house"]["house_num"] == "204"


def test_duplicate_user_registration_fails(client):
    """Test that registering with an existing username returns 400."""
    payload = {
        "username": "john_doe",
        "password": "AnotherPassword!",
        "apartment_block_num": "Block B",
        "house_num": "204"
    }
    response = client.post("/auth/register", json=payload)
    assert response.status_code == 400
    assert "already taken" in response.json()["detail"]


def test_user_login(client):
    """Test login with the newly created resident user."""
    response = client.post(
        "/auth/login",
        json={"username": "john_doe", "password": "Password123!"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["user"]["username"] == "john_doe"
    assert data["user"]["isAdmin"] is False


def test_invalid_login(client):
    """Test login with incorrect password returns 401."""
    response = client.post(
        "/auth/login",
        json={"username": "john_doe", "password": "WrongPassword!"}
    )
    assert response.status_code == 401


def test_get_current_user_profile(client):
    """Test getting profile using the bearer token."""
    login_resp = client.post(
        "/auth/login",
        json={"username": "john_doe", "password": "Password123!"}
    )
    token = login_resp.json()["access_token"]

    response = client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "john_doe"
    assert data["house"]["house_num"] == "204"


def test_apartment_block_case_insensitivity(client):
    """Test that different casings of the apartment block link to the exact same house record."""
    # First user with Title Case
    resp1 = client.post("/auth/register", json={
        "username": "resident_title",
        "password": "Password123!",
        "apartment_block_num": "Tower Alpha",
        "house_num": "101"
    })
    assert resp1.status_code == 201
    house_id_1 = resp1.json()["houseid"]

    # Second user with lower case
    resp2 = client.post("/auth/register", json={
        "username": "resident_lower",
        "password": "Password123!",
        "apartment_block_num": "tower alpha",
        "house_num": "101"
    })
    assert resp2.status_code == 201
    house_id_2 = resp2.json()["houseid"]

    # Third user with UPPER CASE
    resp3 = client.post("/auth/register", json={
        "username": "resident_upper",
        "password": "Password123!",
        "apartment_block_num": "TOWER ALPHA",
        "house_num": "101"
    })
    assert resp3.status_code == 201
    house_id_3 = resp3.json()["houseid"]

    # All three must map to the same houseid without creating duplicate houses
    assert house_id_1 == house_id_2 == house_id_3

