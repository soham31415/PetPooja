import uuid
import pytest


async def test_bill_session_not_found(client):
    resp = await client.get(f"/api/v1/sessions/{uuid.uuid4()}/bill")
    assert resp.status_code == 404


async def test_bill_no_orders(client, user_factory, session_factory):
    _, headers = await user_factory.create_and_login("billhost1")
    session = await session_factory.create(headers)

    resp = await client.get(f"/api/v1/sessions/{session['id']}/bill")
    assert resp.status_code == 200
    data = resp.json()
    assert data["session_id"] == session["id"]
    assert data["grand_total"] == 0.0
    # The host is automatically added as a participant when the session is created.
    assert len(data["per_person"]) == 1
    assert data["per_person"][0]["total"] == 0.0
    assert data["per_person"][0]["items"] == []


async def test_bill_assigned_items(client, user_factory, restaurant_factory, session_factory):
    _, owner_headers = await user_factory.create_and_login("billowner1")
    restaurant = await restaurant_factory.create(owner_headers, name="BillRest1")
    item = await restaurant_factory.add_menu_item(owner_headers, restaurant["id"], name="Pizza", price=10.0)

    host_user, host_headers = await user_factory.create_and_login("billhost2")
    session = await session_factory.create(host_headers, restaurant_id=restaurant["id"])

    guest_user, guest_headers = await user_factory.create_and_login("billguest2")
    await session_factory.join(guest_headers, session["id"])

    # Order with one item assigned to the guest
    create_resp = await client.post(
        "/api/v1/orders/",
        json={
            "session_id": session["id"],
            "items": [{"menu_item_id": item["id"], "quantity": 2, "assigned_user_id": guest_user["id"]}],
        },
        headers=host_headers,
    )
    assert create_resp.status_code == 200

    bill_resp = await client.get(f"/api/v1/sessions/{session['id']}/bill")
    assert bill_resp.status_code == 200
    data = bill_resp.json()
    assert data["grand_total"] == 20.0

    shares = {p["user_id"]: p for p in data["per_person"]}
    assert shares[guest_user["id"]]["total"] == 20.0
    assert shares[host_user["id"]]["total"] == 0.0
    assert shares[guest_user["id"]]["items"][0]["is_shared"] is False


async def test_bill_shared_items_split_equally(client, user_factory, restaurant_factory, session_factory):
    _, owner_headers = await user_factory.create_and_login("billowner2")
    restaurant = await restaurant_factory.create(owner_headers, name="BillRest2")
    item = await restaurant_factory.add_menu_item(owner_headers, restaurant["id"], name="Nachos", price=10.0)

    host_user, host_headers = await user_factory.create_and_login("billhost3")
    session = await session_factory.create(host_headers, restaurant_id=restaurant["id"])

    guest_user, guest_headers = await user_factory.create_and_login("billguest3")
    await session_factory.join(guest_headers, session["id"])

    # Unassigned item: split between 2 active participants
    create_resp = await client.post(
        "/api/v1/orders/",
        json={"session_id": session["id"], "items": [{"menu_item_id": item["id"], "quantity": 1}]},
        headers=host_headers,
    )
    assert create_resp.status_code == 200

    bill_resp = await client.get(f"/api/v1/sessions/{session['id']}/bill")
    data = bill_resp.json()
    assert data["grand_total"] == 10.0

    shares = {p["user_id"]: p for p in data["per_person"]}
    assert shares[host_user["id"]]["total"] == 5.0
    assert shares[guest_user["id"]]["total"] == 5.0
    assert shares[host_user["id"]]["items"][0]["is_shared"] is True


async def test_bill_remainder_distribution(client, user_factory, restaurant_factory, session_factory):
    """An item priced such that splitting leaves remainder cents should distribute them deterministically."""
    _, owner_headers = await user_factory.create_and_login("billowner3")
    restaurant = await restaurant_factory.create(owner_headers, name="BillRest3")
    item = await restaurant_factory.add_menu_item(owner_headers, restaurant["id"], name="Soup", price=10.0)

    host_user, host_headers = await user_factory.create_and_login("billhost4")
    session = await session_factory.create(host_headers, restaurant_id=restaurant["id"])

    # Two more participants -> 3 total participants splitting $10 -> 333,333,334 cents
    guest1_user, guest1_headers = await user_factory.create_and_login("billguest4")
    guest2_user, guest2_headers = await user_factory.create_and_login("billguest5")
    await session_factory.join(guest1_headers, session["id"])
    await session_factory.join(guest2_headers, session["id"])

    await client.post(
        "/api/v1/orders/",
        json={"session_id": session["id"], "items": [{"menu_item_id": item["id"], "quantity": 1}]},
        headers=host_headers,
    )

    bill_resp = await client.get(f"/api/v1/sessions/{session['id']}/bill")
    data = bill_resp.json()
    assert data["grand_total"] == 10.0

    totals = sorted(p["total"] for p in data["per_person"])
    assert totals == [3.33, 3.33, 3.34]
    assert round(sum(totals), 2) == 10.0
