import pytest


async def test_get_table_info(client, user_factory, restaurant_factory):
    _, owner_headers = await user_factory.create_and_login("table_owner1")
    restaurant = await restaurant_factory.create(owner_headers, name="TableInfoRest")
    table = await restaurant_factory.add_table(owner_headers, restaurant["id"], label="T1")

    resp = await client.get(f"/api/v1/tables/{table['qr_token']}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["table_id"] == table["id"]
    assert data["label"] == "T1"
    assert data["restaurant_id"] == restaurant["id"]
    assert data["restaurant_name"] == "TableInfoRest"
    assert data["active_session_id"] is None


async def test_get_table_info_not_found(client):
    resp = await client.get("/api/v1/tables/nonexistent-token")
    assert resp.status_code == 404


async def test_start_session_from_table(client, user_factory, restaurant_factory):
    _, owner_headers = await user_factory.create_and_login("table_owner2")
    restaurant = await restaurant_factory.create(owner_headers, name="TableSessRest")
    table = await restaurant_factory.add_table(owner_headers, restaurant["id"], label="T1")

    _, scanner_headers = await user_factory.create_and_login("scanner1")
    resp = await client.post(f"/api/v1/tables/{table['qr_token']}/session", headers=scanner_headers)
    assert resp.status_code == 200
    session = resp.json()
    assert session["table_id"] == table["id"]
    assert session["restaurant_id"] == restaurant["id"]
    assert session["status"] == "active"

    # Table info should now show the active session
    info_resp = await client.get(f"/api/v1/tables/{table['qr_token']}")
    assert info_resp.json()["active_session_id"] == session["id"]


async def test_join_session_via_table(client, user_factory, restaurant_factory):
    _, owner_headers = await user_factory.create_and_login("table_owner3")
    restaurant = await restaurant_factory.create(owner_headers, name="TableJoinRest")
    table = await restaurant_factory.add_table(owner_headers, restaurant["id"], label="T1")

    _, first_headers = await user_factory.create_and_login("scanner2")
    first_session = (await client.post(f"/api/v1/tables/{table['qr_token']}/session", headers=first_headers)).json()

    _, second_headers = await user_factory.create_and_login("scanner3")
    second_resp = await client.post(f"/api/v1/tables/{table['qr_token']}/session", headers=second_headers)
    assert second_resp.status_code == 200
    second_session = second_resp.json()

    # Should join the same active session, not create a new one
    assert second_session["id"] == first_session["id"]

    participants_resp = await client.get(f"/api/v1/sessions/{first_session['id']}/participants")
    usernames = {p["username"] for p in participants_resp.json()}
    assert {"scanner2", "scanner3"}.issubset(usernames)


async def test_start_or_join_session_requires_auth(client, user_factory, restaurant_factory):
    _, owner_headers = await user_factory.create_and_login("table_owner4")
    restaurant = await restaurant_factory.create(owner_headers, name="TableAuthRest")
    table = await restaurant_factory.add_table(owner_headers, restaurant["id"], label="T1")

    resp = await client.post(f"/api/v1/tables/{table['qr_token']}/session")
    assert resp.status_code == 401


async def test_start_session_from_table_not_found(client, user_factory):
    _, headers = await user_factory.create_and_login("scanner4")
    resp = await client.post("/api/v1/tables/bad-token/session", headers=headers)
    assert resp.status_code == 400


async def test_new_session_started_after_previous_closed(client, user_factory, restaurant_factory):
    """If the table's only session was closed, a new scan should start a new session."""
    _, owner_headers = await user_factory.create_and_login("table_owner5")
    restaurant = await restaurant_factory.create(owner_headers, name="TableReuseRest")
    table = await restaurant_factory.add_table(owner_headers, restaurant["id"], label="T1")

    _, host_headers = await user_factory.create_and_login("scanner5")
    first_session = (await client.post(f"/api/v1/tables/{table['qr_token']}/session", headers=host_headers)).json()

    # Close the session
    close_resp = await client.patch(
        f"/api/v1/sessions/{first_session['id']}/status", json={"status": "closed"}, headers=host_headers
    )
    assert close_resp.status_code == 200

    _, new_host_headers = await user_factory.create_and_login("scanner6")
    second_session = (await client.post(f"/api/v1/tables/{table['qr_token']}/session", headers=new_host_headers)).json()

    assert second_session["id"] != first_session["id"]
    assert second_session["status"] == "active"
