import uuid
import pytest


async def _setup_session_with_menu(client, user_factory, restaurant_factory, session_factory):
    """Create an owner+restaurant+menu item, a host who creates a session at that
    restaurant, and a second participant who joins. Returns a dict of useful refs."""
    _, owner_headers = await user_factory.create_and_login("rest_owner_" + uuid.uuid4().hex[:8])
    restaurant = await restaurant_factory.create(owner_headers, name="Order Rest " + uuid.uuid4().hex[:6])
    menu_item = await restaurant_factory.add_menu_item(
        owner_headers, restaurant["id"], name="Taco", price=5.0, tags=["spicy"]
    )

    host_user, host_headers = await user_factory.create_and_login("host_" + uuid.uuid4().hex[:8])
    session = await session_factory.create(host_headers, restaurant_id=restaurant["id"])

    guest_user, guest_headers = await user_factory.create_and_login("guest_" + uuid.uuid4().hex[:8])
    await session_factory.join(guest_headers, session["id"])

    return {
        "owner_headers": owner_headers,
        "restaurant": restaurant,
        "menu_item": menu_item,
        "host_user": host_user,
        "host_headers": host_headers,
        "session": session,
        "guest_user": guest_user,
        "guest_headers": guest_headers,
    }


async def test_create_order_success(client, user_factory, restaurant_factory, session_factory):
    ctx = await _setup_session_with_menu(client, user_factory, restaurant_factory, session_factory)

    resp = await client.post(
        "/api/v1/orders/",
        json={
            "session_id": ctx["session"]["id"],
            "items": [{"menu_item_id": ctx["menu_item"]["id"], "quantity": 2}],
        },
        headers=ctx["host_headers"],
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "pending"
    assert len(data["items"]) == 1
    assert data["items"][0]["quantity"] == 2
    assert data["items"][0]["menu_item"]["name"] == "Taco"


async def test_create_order_requires_auth(client, user_factory, restaurant_factory, session_factory):
    ctx = await _setup_session_with_menu(client, user_factory, restaurant_factory, session_factory)
    resp = await client.post(
        "/api/v1/orders/",
        json={"session_id": ctx["session"]["id"], "items": [{"menu_item_id": ctx["menu_item"]["id"], "quantity": 1}]},
    )
    assert resp.status_code == 401


async def test_create_order_non_participant_forbidden(client, user_factory, restaurant_factory, session_factory):
    ctx = await _setup_session_with_menu(client, user_factory, restaurant_factory, session_factory)
    _, outsider_headers = await user_factory.create_and_login("outsider_" + uuid.uuid4().hex[:8])

    resp = await client.post(
        "/api/v1/orders/",
        json={"session_id": ctx["session"]["id"], "items": [{"menu_item_id": ctx["menu_item"]["id"], "quantity": 1}]},
        headers=outsider_headers,
    )
    assert resp.status_code == 403


async def test_create_order_session_not_found(client, user_factory, restaurant_factory, session_factory):
    ctx = await _setup_session_with_menu(client, user_factory, restaurant_factory, session_factory)
    resp = await client.post(
        "/api/v1/orders/",
        json={"session_id": str(uuid.uuid4()), "items": [{"menu_item_id": ctx["menu_item"]["id"], "quantity": 1}]},
        headers=ctx["host_headers"],
    )
    assert resp.status_code == 400


async def test_create_order_menu_item_not_found(client, user_factory, restaurant_factory, session_factory):
    ctx = await _setup_session_with_menu(client, user_factory, restaurant_factory, session_factory)
    resp = await client.post(
        "/api/v1/orders/",
        json={"session_id": ctx["session"]["id"], "items": [{"menu_item_id": 99999, "quantity": 1}]},
        headers=ctx["host_headers"],
    )
    assert resp.status_code == 400


async def test_create_order_menu_item_wrong_restaurant(client, user_factory, restaurant_factory, session_factory):
    ctx = await _setup_session_with_menu(client, user_factory, restaurant_factory, session_factory)

    # Create a different restaurant + menu item
    _, owner2_headers = await user_factory.create_and_login("owner2_" + uuid.uuid4().hex[:8])
    restaurant2 = await restaurant_factory.create(owner2_headers, name="Other Rest")
    other_item = await restaurant_factory.add_menu_item(owner2_headers, restaurant2["id"], name="Other Item")

    resp = await client.post(
        "/api/v1/orders/",
        json={"session_id": ctx["session"]["id"], "items": [{"menu_item_id": other_item["id"], "quantity": 1}]},
        headers=ctx["host_headers"],
    )
    assert resp.status_code == 400


async def test_create_order_no_restaurant_session(client, user_factory, session_factory):
    _, headers = await user_factory.create_and_login("noresto_" + uuid.uuid4().hex[:8])
    session = await session_factory.create(headers, restaurant_id=None)
    resp = await client.post(
        "/api/v1/orders/",
        json={"session_id": session["id"], "items": [{"menu_item_id": 1, "quantity": 1}]},
        headers=headers,
    )
    assert resp.status_code == 400


async def test_get_order(client, user_factory, restaurant_factory, session_factory):
    ctx = await _setup_session_with_menu(client, user_factory, restaurant_factory, session_factory)
    create_resp = await client.post(
        "/api/v1/orders/",
        json={"session_id": ctx["session"]["id"], "items": [{"menu_item_id": ctx["menu_item"]["id"], "quantity": 1}]},
        headers=ctx["host_headers"],
    )
    order_id = create_resp.json()["id"]

    resp = await client.get(f"/api/v1/orders/{order_id}")
    assert resp.status_code == 200
    assert resp.json()["id"] == order_id


async def test_get_order_not_found(client):
    resp = await client.get("/api/v1/orders/99999")
    assert resp.status_code == 404


async def test_get_orders_for_session(client, user_factory, restaurant_factory, session_factory):
    ctx = await _setup_session_with_menu(client, user_factory, restaurant_factory, session_factory)
    await client.post(
        "/api/v1/orders/",
        json={"session_id": ctx["session"]["id"], "items": [{"menu_item_id": ctx["menu_item"]["id"], "quantity": 1}]},
        headers=ctx["host_headers"],
    )
    await client.post(
        "/api/v1/orders/",
        json={"session_id": ctx["session"]["id"], "items": [{"menu_item_id": ctx["menu_item"]["id"], "quantity": 3}]},
        headers=ctx["guest_headers"],
    )

    resp = await client.get(f"/api/v1/orders/session/{ctx['session']['id']}")
    assert resp.status_code == 200
    assert len(resp.json()) == 2


async def test_update_order_status_owner_flow(client, user_factory, restaurant_factory, session_factory):
    ctx = await _setup_session_with_menu(client, user_factory, restaurant_factory, session_factory)
    create_resp = await client.post(
        "/api/v1/orders/",
        json={"session_id": ctx["session"]["id"], "items": [{"menu_item_id": ctx["menu_item"]["id"], "quantity": 1}]},
        headers=ctx["host_headers"],
    )
    order_id = create_resp.json()["id"]

    # Non-owner cannot update
    resp = await client.patch(
        f"/api/v1/orders/{order_id}/status", json={"status": "confirmed"}, headers=ctx["host_headers"]
    )
    assert resp.status_code == 403

    # Owner can confirm
    resp = await client.patch(
        f"/api/v1/orders/{order_id}/status", json={"status": "confirmed"}, headers=ctx["owner_headers"]
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "confirmed"

    # Owner can mark paid
    resp = await client.patch(
        f"/api/v1/orders/{order_id}/status", json={"status": "paid"}, headers=ctx["owner_headers"]
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "paid"

    # Cannot transition from paid
    resp = await client.patch(
        f"/api/v1/orders/{order_id}/status", json={"status": "confirmed"}, headers=ctx["owner_headers"]
    )
    assert resp.status_code == 400


async def test_update_order_status_invalid_transition_skip(client, user_factory, restaurant_factory, session_factory):
    ctx = await _setup_session_with_menu(client, user_factory, restaurant_factory, session_factory)
    create_resp = await client.post(
        "/api/v1/orders/",
        json={"session_id": ctx["session"]["id"], "items": [{"menu_item_id": ctx["menu_item"]["id"], "quantity": 1}]},
        headers=ctx["host_headers"],
    )
    order_id = create_resp.json()["id"]

    # pending -> paid directly is invalid
    resp = await client.patch(
        f"/api/v1/orders/{order_id}/status", json={"status": "paid"}, headers=ctx["owner_headers"]
    )
    assert resp.status_code == 400


async def test_add_item_to_order(client, user_factory, restaurant_factory, session_factory):
    ctx = await _setup_session_with_menu(client, user_factory, restaurant_factory, session_factory)
    create_resp = await client.post(
        "/api/v1/orders/",
        json={"session_id": ctx["session"]["id"], "items": [{"menu_item_id": ctx["menu_item"]["id"], "quantity": 1}]},
        headers=ctx["host_headers"],
    )
    order_id = create_resp.json()["id"]

    resp = await client.post(
        f"/api/v1/orders/{order_id}/items",
        json={"menu_item_id": ctx["menu_item"]["id"], "quantity": 2},
        headers=ctx["guest_headers"],
    )
    assert resp.status_code == 200
    assert len(resp.json()["items"]) == 2


async def test_add_item_to_order_non_participant_forbidden(client, user_factory, restaurant_factory, session_factory):
    ctx = await _setup_session_with_menu(client, user_factory, restaurant_factory, session_factory)
    create_resp = await client.post(
        "/api/v1/orders/",
        json={"session_id": ctx["session"]["id"], "items": [{"menu_item_id": ctx["menu_item"]["id"], "quantity": 1}]},
        headers=ctx["host_headers"],
    )
    order_id = create_resp.json()["id"]

    _, outsider_headers = await user_factory.create_and_login("outsider2_" + uuid.uuid4().hex[:8])
    resp = await client.post(
        f"/api/v1/orders/{order_id}/items",
        json={"menu_item_id": ctx["menu_item"]["id"], "quantity": 1},
        headers=outsider_headers,
    )
    assert resp.status_code == 403


async def test_add_item_to_non_pending_order_fails(client, user_factory, restaurant_factory, session_factory):
    ctx = await _setup_session_with_menu(client, user_factory, restaurant_factory, session_factory)
    create_resp = await client.post(
        "/api/v1/orders/",
        json={"session_id": ctx["session"]["id"], "items": [{"menu_item_id": ctx["menu_item"]["id"], "quantity": 1}]},
        headers=ctx["host_headers"],
    )
    order_id = create_resp.json()["id"]

    await client.patch(f"/api/v1/orders/{order_id}/status", json={"status": "confirmed"}, headers=ctx["owner_headers"])

    resp = await client.post(
        f"/api/v1/orders/{order_id}/items",
        json={"menu_item_id": ctx["menu_item"]["id"], "quantity": 1},
        headers=ctx["host_headers"],
    )
    assert resp.status_code == 400


async def test_assign_order_item(client, user_factory, restaurant_factory, session_factory):
    ctx = await _setup_session_with_menu(client, user_factory, restaurant_factory, session_factory)
    create_resp = await client.post(
        "/api/v1/orders/",
        json={"session_id": ctx["session"]["id"], "items": [{"menu_item_id": ctx["menu_item"]["id"], "quantity": 1}]},
        headers=ctx["host_headers"],
    )
    order = create_resp.json()
    item_id = order["items"][0]["id"]

    resp = await client.patch(
        f"/api/v1/orders/{order['id']}/items/{item_id}/assign",
        json={"assigned_user_id": ctx["guest_user"]["id"]},
        headers=ctx["host_headers"],
    )
    assert resp.status_code == 200
    assert resp.json()["items"][0]["assigned_user_id"] == ctx["guest_user"]["id"]

    # Reassign back to shared pool
    resp = await client.patch(
        f"/api/v1/orders/{order['id']}/items/{item_id}/assign",
        json={"assigned_user_id": None},
        headers=ctx["host_headers"],
    )
    assert resp.status_code == 200
    assert resp.json()["items"][0]["assigned_user_id"] is None


async def test_assign_order_item_to_non_participant_fails(client, user_factory, restaurant_factory, session_factory):
    ctx = await _setup_session_with_menu(client, user_factory, restaurant_factory, session_factory)
    create_resp = await client.post(
        "/api/v1/orders/",
        json={"session_id": ctx["session"]["id"], "items": [{"menu_item_id": ctx["menu_item"]["id"], "quantity": 1}]},
        headers=ctx["host_headers"],
    )
    order = create_resp.json()
    item_id = order["items"][0]["id"]

    _, outsider_headers = await user_factory.create_and_login("outsider3_" + uuid.uuid4().hex[:8])
    me_resp = await client.get("/api/v1/users/me", headers=outsider_headers)
    outsider_id = me_resp.json()["id"]

    resp = await client.patch(
        f"/api/v1/orders/{order['id']}/items/{item_id}/assign",
        json={"assigned_user_id": outsider_id},
        headers=ctx["host_headers"],
    )
    assert resp.status_code == 400


async def test_assign_order_item_not_found(client, user_factory, restaurant_factory, session_factory):
    ctx = await _setup_session_with_menu(client, user_factory, restaurant_factory, session_factory)
    create_resp = await client.post(
        "/api/v1/orders/",
        json={"session_id": ctx["session"]["id"], "items": [{"menu_item_id": ctx["menu_item"]["id"], "quantity": 1}]},
        headers=ctx["host_headers"],
    )
    order = create_resp.json()

    resp = await client.patch(
        f"/api/v1/orders/{order['id']}/items/99999/assign",
        json={"assigned_user_id": None},
        headers=ctx["host_headers"],
    )
    assert resp.status_code == 400


async def test_remove_item_from_order(client, user_factory, restaurant_factory, session_factory):
    ctx = await _setup_session_with_menu(client, user_factory, restaurant_factory, session_factory)
    create_resp = await client.post(
        "/api/v1/orders/",
        json={
            "session_id": ctx["session"]["id"],
            "items": [
                {"menu_item_id": ctx["menu_item"]["id"], "quantity": 1},
                {"menu_item_id": ctx["menu_item"]["id"], "quantity": 2},
            ],
        },
        headers=ctx["host_headers"],
    )
    order = create_resp.json()
    assert len(order["items"]) == 2
    item_id = order["items"][0]["id"]

    resp = await client.delete(f"/api/v1/orders/{order['id']}/items/{item_id}", headers=ctx["guest_headers"])
    assert resp.status_code == 200
    assert len(resp.json()["items"]) == 1


async def test_remove_item_from_order_non_participant_forbidden(client, user_factory, restaurant_factory, session_factory):
    ctx = await _setup_session_with_menu(client, user_factory, restaurant_factory, session_factory)
    create_resp = await client.post(
        "/api/v1/orders/",
        json={"session_id": ctx["session"]["id"], "items": [{"menu_item_id": ctx["menu_item"]["id"], "quantity": 1}]},
        headers=ctx["host_headers"],
    )
    order = create_resp.json()
    item_id = order["items"][0]["id"]

    _, outsider_headers = await user_factory.create_and_login("outsider4_" + uuid.uuid4().hex[:8])
    resp = await client.delete(f"/api/v1/orders/{order['id']}/items/{item_id}", headers=outsider_headers)
    assert resp.status_code == 403


async def test_remove_item_from_non_pending_order_fails(client, user_factory, restaurant_factory, session_factory):
    ctx = await _setup_session_with_menu(client, user_factory, restaurant_factory, session_factory)
    create_resp = await client.post(
        "/api/v1/orders/",
        json={"session_id": ctx["session"]["id"], "items": [{"menu_item_id": ctx["menu_item"]["id"], "quantity": 1}]},
        headers=ctx["host_headers"],
    )
    order = create_resp.json()
    item_id = order["items"][0]["id"]

    await client.patch(f"/api/v1/orders/{order['id']}/status", json={"status": "confirmed"}, headers=ctx["owner_headers"])

    resp = await client.delete(f"/api/v1/orders/{order['id']}/items/{item_id}", headers=ctx["host_headers"])
    assert resp.status_code == 400


async def test_remove_item_not_found(client, user_factory, restaurant_factory, session_factory):
    ctx = await _setup_session_with_menu(client, user_factory, restaurant_factory, session_factory)
    create_resp = await client.post(
        "/api/v1/orders/",
        json={"session_id": ctx["session"]["id"], "items": [{"menu_item_id": ctx["menu_item"]["id"], "quantity": 1}]},
        headers=ctx["host_headers"],
    )
    order = create_resp.json()

    resp = await client.delete(f"/api/v1/orders/{order['id']}/items/99999", headers=ctx["host_headers"])
    assert resp.status_code == 400
