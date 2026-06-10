import pytest


async def test_analytics_requires_auth(client, user_factory, restaurant_factory):
    _, owner_headers = await user_factory.create_and_login("analyticsowner1")
    restaurant = await restaurant_factory.create(owner_headers, name="AnalyticsRest1")

    resp = await client.get(f"/api/v1/restaurants/{restaurant['id']}/analytics")
    assert resp.status_code == 401


async def test_analytics_owner_only(client, user_factory, restaurant_factory):
    _, owner_headers = await user_factory.create_and_login("analyticsowner2")
    _, other_headers = await user_factory.create_and_login("analyticsintruder1")
    restaurant = await restaurant_factory.create(owner_headers, name="AnalyticsRest2")

    resp = await client.get(f"/api/v1/restaurants/{restaurant['id']}/analytics", headers=other_headers)
    assert resp.status_code == 403


async def test_analytics_empty(client, user_factory, restaurant_factory):
    _, owner_headers = await user_factory.create_and_login("analyticsowner3")
    restaurant = await restaurant_factory.create(owner_headers, name="AnalyticsRest3")

    resp = await client.get(f"/api/v1/restaurants/{restaurant['id']}/analytics", headers=owner_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["restaurant_id"] == restaurant["id"]
    assert data["total_orders"] == 0
    assert data["orders_by_status"] == {}
    assert data["total_revenue"] == 0.0
    assert data["average_participants_per_session"] == 0.0
    assert data["top_menu_items"] == []


async def test_analytics_not_found(client, user_factory):
    _, headers = await user_factory.create_and_login("analyticsowner4")
    resp = await client.get("/api/v1/restaurants/99999/analytics", headers=headers)
    assert resp.status_code == 404


async def test_analytics_with_orders(client, user_factory, restaurant_factory, session_factory):
    _, owner_headers = await user_factory.create_and_login("analyticsowner5")
    restaurant = await restaurant_factory.create(owner_headers, name="AnalyticsRest5")
    item1 = await restaurant_factory.add_menu_item(owner_headers, restaurant["id"], name="Burger", price=8.0)
    item2 = await restaurant_factory.add_menu_item(owner_headers, restaurant["id"], name="Fries", price=3.0)

    host_user, host_headers = await user_factory.create_and_login("analyticshost1")
    session = await session_factory.create(host_headers, restaurant_id=restaurant["id"])

    guest_user, guest_headers = await user_factory.create_and_login("analyticsguest1")
    await session_factory.join(guest_headers, session["id"])

    # Order 1: 2 burgers + 1 fries
    order1_resp = await client.post(
        "/api/v1/orders/",
        json={
            "session_id": session["id"],
            "items": [
                {"menu_item_id": item1["id"], "quantity": 2},
                {"menu_item_id": item2["id"], "quantity": 1},
            ],
        },
        headers=host_headers,
    )
    order1 = order1_resp.json()

    # Order 2: 1 fries
    await client.post(
        "/api/v1/orders/",
        json={"session_id": session["id"], "items": [{"menu_item_id": item2["id"], "quantity": 1}]},
        headers=guest_headers,
    )

    # Confirm order 1
    await client.patch(
        f"/api/v1/orders/{order1['id']}/status", json={"status": "confirmed"}, headers=owner_headers
    )

    resp = await client.get(f"/api/v1/restaurants/{restaurant['id']}/analytics", headers=owner_headers)
    assert resp.status_code == 200
    data = resp.json()

    assert data["total_orders"] == 2
    assert data["orders_by_status"]["confirmed"] == 1
    assert data["orders_by_status"]["pending"] == 1

    # Revenue: 2*8 + 1*3 + 1*3 = 22.0
    assert data["total_revenue"] == 22.0

    # 2 participants in 1 session -> avg group size 2
    assert data["average_participants_per_session"] == 2.0

    # Top item should be Burger with quantity_ordered=2
    top_names = [i["name"] for i in data["top_menu_items"]]
    assert "Burger" in top_names
    burger_stat = next(i for i in data["top_menu_items"] if i["name"] == "Burger")
    assert burger_stat["quantity_ordered"] == 2
    assert burger_stat["revenue"] == 16.0

    fries_stat = next(i for i in data["top_menu_items"] if i["name"] == "Fries")
    assert fries_stat["quantity_ordered"] == 2
    assert fries_stat["revenue"] == 6.0
