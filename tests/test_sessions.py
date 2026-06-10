import uuid
import pytest


async def test_create_session_no_restaurant(client, user_factory):
    _, headers = await user_factory.create_and_login("host1")
    resp = await client.post("/api/v1/sessions/", json={"restaurant_id": None}, headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["restaurant_id"] is None
    assert data["status"] == "active"
    assert data["host_id"] is not None


async def test_create_session_requires_auth(client):
    resp = await client.post("/api/v1/sessions/", json={"restaurant_id": None})
    assert resp.status_code == 401


async def test_create_session_with_restaurant(client, user_factory, restaurant_factory):
    _, headers = await user_factory.create_and_login("host2")
    restaurant = await restaurant_factory.create(headers, name="SessionRest")
    resp = await client.post("/api/v1/sessions/", json={"restaurant_id": restaurant["id"]}, headers=headers)
    assert resp.status_code == 200
    assert resp.json()["restaurant_id"] == restaurant["id"]


async def test_create_session_invalid_restaurant(client, user_factory):
    _, headers = await user_factory.create_and_login("host3")
    resp = await client.post("/api/v1/sessions/", json={"restaurant_id": 99999}, headers=headers)
    assert resp.status_code == 400


async def test_get_session_details(client, user_factory, session_factory):
    _, headers = await user_factory.create_and_login("host4")
    session = await session_factory.create(headers)

    resp = await client.get(f"/api/v1/sessions/{session['id']}")
    assert resp.status_code == 200
    assert resp.json()["id"] == session["id"]


async def test_get_session_not_found(client):
    resp = await client.get(f"/api/v1/sessions/{uuid.uuid4()}")
    assert resp.status_code == 404


async def test_join_session(client, user_factory, session_factory):
    _, host_headers = await user_factory.create_and_login("host5")
    _, guest_headers = await user_factory.create_and_login("guestjoin1")

    session = await session_factory.create(host_headers)
    resp = await client.post(f"/api/v1/sessions/{session['id']}/join", headers=guest_headers)
    assert resp.status_code == 200

    participants_resp = await client.get(f"/api/v1/sessions/{session['id']}/participants")
    assert participants_resp.status_code == 200
    usernames = {p["username"] for p in participants_resp.json()}
    assert {"host5", "guestjoin1"}.issubset(usernames)


async def test_join_session_idempotent(client, user_factory, session_factory):
    _, host_headers = await user_factory.create_and_login("host6")
    _, guest_headers = await user_factory.create_and_login("guestjoin2")

    session = await session_factory.create(host_headers)
    resp1 = await client.post(f"/api/v1/sessions/{session['id']}/join", headers=guest_headers)
    resp2 = await client.post(f"/api/v1/sessions/{session['id']}/join", headers=guest_headers)
    assert resp1.status_code == 200
    assert resp2.status_code == 200


async def test_join_nonexistent_session(client, user_factory):
    _, headers = await user_factory.create_and_login("guestjoin3")
    resp = await client.post(f"/api/v1/sessions/{uuid.uuid4()}/join", headers=headers)
    assert resp.status_code == 400


async def test_join_session_requires_auth(client, user_factory, session_factory):
    _, headers = await user_factory.create_and_login("host7")
    session = await session_factory.create(headers)
    resp = await client.post(f"/api/v1/sessions/{session['id']}/join")
    assert resp.status_code == 401


async def test_get_participants_empty_for_unknown_session(client):
    resp = await client.get(f"/api/v1/sessions/{uuid.uuid4()}/participants")
    assert resp.status_code == 200
    assert resp.json() == []


async def test_update_session_status_close(client, user_factory, session_factory):
    _, headers = await user_factory.create_and_login("host8")
    session = await session_factory.create(headers)

    resp = await client.patch(
        f"/api/v1/sessions/{session['id']}/status", json={"status": "closed"}, headers=headers
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "closed"


async def test_update_session_status_only_host(client, user_factory, session_factory):
    _, host_headers = await user_factory.create_and_login("host9")
    _, other_headers = await user_factory.create_and_login("notthehost1")

    session = await session_factory.create(host_headers)
    resp = await client.patch(
        f"/api/v1/sessions/{session['id']}/status", json={"status": "closed"}, headers=other_headers
    )
    assert resp.status_code == 403


async def test_update_session_status_invalid_transition(client, user_factory, session_factory):
    _, headers = await user_factory.create_and_login("host10")
    session = await session_factory.create(headers)

    # Close it first
    resp = await client.patch(
        f"/api/v1/sessions/{session['id']}/status", json={"status": "closed"}, headers=headers
    )
    assert resp.status_code == 200

    # Now try to transition again from closed -> active (invalid)
    resp = await client.patch(
        f"/api/v1/sessions/{session['id']}/status", json={"status": "active"}, headers=headers
    )
    assert resp.status_code == 400


async def test_update_session_status_not_found(client, user_factory):
    _, headers = await user_factory.create_and_login("host11")
    resp = await client.patch(
        f"/api/v1/sessions/{uuid.uuid4()}/status", json={"status": "closed"}, headers=headers
    )
    assert resp.status_code == 400


async def test_get_recommendations_empty_menu(client, user_factory, restaurant_factory, session_factory):
    _, headers = await user_factory.create_and_login("host12")
    restaurant = await restaurant_factory.create(headers, name="RecRest")
    session = await session_factory.create(headers, restaurant_id=restaurant["id"])

    resp = await client.get(f"/api/v1/sessions/{session['id']}/recommendations")
    assert resp.status_code == 200
    assert resp.json() == []


async def test_get_recommendations_session_not_found(client):
    resp = await client.get(f"/api/v1/sessions/{uuid.uuid4()}/recommendations")
    assert resp.status_code == 404


async def test_get_recommendations_with_preferences_and_restrictions(
    client, user_factory, restaurant_factory, session_factory
):
    _, headers = await user_factory.create_and_login("host13")
    restaurant = await restaurant_factory.create(headers, name="RecRest2")

    # Add menu items
    spicy_vegan = await restaurant_factory.add_menu_item(
        headers, restaurant["id"], name="Spicy Vegan Curry", tags=["spicy", "vegan"]
    )
    meat_dish = await restaurant_factory.add_menu_item(
        headers, restaurant["id"], name="Steak", tags=["meat"]
    )
    plain_vegan = await restaurant_factory.add_menu_item(
        headers, restaurant["id"], name="Vegan Salad", tags=["vegan"]
    )

    # Update host's taste profile: vegan restriction + spicy preference
    me_resp = await client.get("/api/v1/users/me", headers=headers)
    user_id = me_resp.json()["id"]
    await client.put(
        f"/api/v1/users/{user_id}/taste_profile",
        json={"preferences": ["spicy"], "daringness": 7, "dietary_restrictions": ["vegan"]},
    )

    session = await session_factory.create(headers, restaurant_id=restaurant["id"])

    resp = await client.get(f"/api/v1/sessions/{session['id']}/recommendations")
    assert resp.status_code == 200
    items = resp.json()
    names = [i["name"] for i in items]

    # Meat dish should be filtered out (doesn't satisfy "vegan" restriction)
    assert "Steak" not in names
    assert "Spicy Vegan Curry" in names
    assert "Vegan Salad" in names

    # Spicy vegan item should be ranked higher (matches preference) than plain vegan
    assert names.index("Spicy Vegan Curry") < names.index("Vegan Salad")
