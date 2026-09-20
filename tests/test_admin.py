import io
import pytest


@pytest.fixture
def admin_token(client):
    resp = client.post("/auth/login", json={
        "username": "admin",
        "password": "AdminSecurePassword123!"
    })
    return resp.json()["access_token"]


@pytest.fixture
def user_token(client):
    client.post("/auth/register", json={
        "username": "bob",
        "password": "Password123!",
        "apartment_block_num": "Block C",
        "house_num": "301"
    })
    resp = client.post("/auth/login", json={
        "username": "bob",
        "password": "Password123!"
    })
    return resp.json()["access_token"]


def test_regular_user_cannot_access_admin_routes(client, user_token):
    """Ensure regular resident receives 403 Forbidden on admin endpoints."""
    response = client.get(
        "/admin/maintenance",
        headers={"Authorization": f"Bearer {user_token}"}
    )
    assert response.status_code == 403
    assert "Administrator privileges required" in response.json()["detail"]


def test_admin_oversee_and_assign_maintenance(client, admin_token, user_token):
    """Test admin overseeing all tickets and assigning technician."""
    # User creates a ticket first
    fake_image = io.BytesIO(b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR")
    files = {"image": ("broken_pipe.png", fake_image, "image/png")}
    create_resp = client.post(
        "/maintenance",
        data={
            "problem_category": "Plumbing",
            "details": "Severe pipe leakage in bathroom"
        },
        files=files,
        headers={"Authorization": f"Bearer {user_token}"}
    )
    assert create_resp.status_code == 201
    ticket_id = create_resp.json()["maintanance_id"]

    # Admin lists all tickets
    admin_list_resp = client.get(
        "/admin/maintenance",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert admin_list_resp.status_code == 200
    all_tickets = admin_list_resp.json()
    assert any(t["maintanance_id"] == ticket_id for t in all_tickets)

    # Admin assigns a technician to the ticket
    assign_payload = {"isAssignedTo": "Carlos (Lead Plumber)"}
    assign_resp = client.patch(
        f"/admin/maintenance/{ticket_id}/assign",
        json=assign_payload,
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert assign_resp.status_code == 200
    updated_ticket = assign_resp.json()
    assert updated_ticket["isAssignedTo"] == "Carlos (Lead Plumber)"

    # Filter assigned
    filtered_resp = client.get(
        "/admin/maintenance?is_assigned=true",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert filtered_resp.status_code == 200
    assigned_tickets = filtered_resp.json()
    assert any(t["maintanance_id"] == ticket_id for t in assigned_tickets)


def test_admin_views_users_and_houses(client, admin_token):
    """Test admin querying user and house directories."""
    users_resp = client.get("/admin/users", headers={"Authorization": f"Bearer {admin_token}"})
    assert users_resp.status_code == 200
    users = users_resp.json()
    assert len(users) >= 2  # Admin + Bob

    houses_resp = client.get("/admin/houses", headers={"Authorization": f"Bearer {admin_token}"})
    assert houses_resp.status_code == 200
    houses = houses_resp.json()
    assert len(houses) >= 1

    stats_resp = client.get("/admin/stats", headers={"Authorization": f"Bearer {admin_token}"})
    assert stats_resp.status_code == 200
    stats = stats_resp.json()
    assert stats["total_maintenance_requests"] >= 1
    assert stats["assigned_requests"] >= 1


def test_admin_filter_by_block_case_insensitive(client, admin_token):
    """Test filtering tickets by block name case-insensitively."""
    # Bob is in "Block C" and has a ticket from test_admin_oversee_and_assign_maintenance
    resp_lower = client.get("/admin/maintenance?block=block c", headers={"Authorization": f"Bearer {admin_token}"})
    assert resp_lower.status_code == 200
    tickets_lower = resp_lower.json()
    assert len(tickets_lower) >= 1

    resp_upper = client.get("/admin/maintenance?block=BLOCK C", headers={"Authorization": f"Bearer {admin_token}"})
    assert resp_upper.status_code == 200
    tickets_upper = resp_upper.json()
    assert len(tickets_upper) >= 1
    assert len(tickets_lower) == len(tickets_upper)

