import pytest


async def test_create_restaurant(client, user_factory):
    _, headers = await user_factory.create_and_login("owner1")
    resp = await client.post(
        "/api/v1/restaurants/", json={"name": "Pizza Place", "address": "1 Main St"}, headers=headers
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "Pizza Place"
    assert data["menu_items"] == []
    assert data["owner_id"] is not None


async def test_create_restaurant_requires_auth(client):
    resp = await client.post("/api/v1/restaurants/", json={"name": "X", "address": "Y"})
    assert resp.status_code == 401


async def test_list_restaurants(client, user_factory, restaurant_factory):
    _, headers = await user_factory.create_and_login("owner2")
    await restaurant_factory.create(headers, name="A")
    await restaurant_factory.create(headers, name="B")

    resp = await client.get("/api/v1/restaurants/")
    assert resp.status_code == 200
    names = {r["name"] for r in resp.json()}
    assert {"A", "B"}.issubset(names)


async def test_list_mine_only_owned(client, user_factory, restaurant_factory):
    _, headers1 = await user_factory.create_and_login("owner3")
    _, headers2 = await user_factory.create_and_login("owner4")

    await restaurant_factory.create(headers1, name="Mine1")
    await restaurant_factory.create(headers2, name="NotMine")

    resp = await client.get("/api/v1/restaurants/mine", headers=headers1)
    assert resp.status_code == 200
    names = {r["name"] for r in resp.json()}
    assert "Mine1" in names
    assert "NotMine" not in names


async def test_list_mine_requires_auth(client):
    resp = await client.get("/api/v1/restaurants/mine")
    assert resp.status_code == 401


async def test_create_menu_item_owner_only(client, user_factory, restaurant_factory):
    _, owner_headers = await user_factory.create_and_login("owner5")
    _, other_headers = await user_factory.create_and_login("intruder1")

    restaurant = await restaurant_factory.create(owner_headers, name="MenuTest")

    # Owner can add
    resp = await client.post(
        f"/api/v1/restaurants/{restaurant['id']}/menu",
        json={"name": "Burger", "description": "Beef burger", "price": 9.5, "tags": ["meat"]},
        headers=owner_headers,
    )
    assert resp.status_code == 200
    item = resp.json()
    assert item["name"] == "Burger"
    assert item["restaurant_id"] == restaurant["id"]

    # Non-owner cannot add
    resp = await client.post(
        f"/api/v1/restaurants/{restaurant['id']}/menu",
        json={"name": "Fries", "description": "Crispy", "price": 3.0, "tags": []},
        headers=other_headers,
    )
    assert resp.status_code == 403


async def test_create_menu_item_restaurant_not_found(client, user_factory):
    _, headers = await user_factory.create_and_login("owner6")
    resp = await client.post(
        "/api/v1/restaurants/99999/menu",
        json={"name": "X", "description": "Y", "price": 1.0, "tags": []},
        headers=headers,
    )
    assert resp.status_code == 404


async def test_list_menu_items(client, user_factory, restaurant_factory):
    _, headers = await user_factory.create_and_login("owner7")
    restaurant = await restaurant_factory.create(headers, name="MenuList")
    await restaurant_factory.add_menu_item(headers, restaurant["id"], name="Item1")
    await restaurant_factory.add_menu_item(headers, restaurant["id"], name="Item2")

    resp = await client.get(f"/api/v1/restaurants/{restaurant['id']}/menu")
    assert resp.status_code == 200
    names = {i["name"] for i in resp.json()}
    assert names == {"Item1", "Item2"}


async def test_list_menu_items_restaurant_not_found(client):
    resp = await client.get("/api/v1/restaurants/99999/menu")
    assert resp.status_code == 404


async def test_create_table_owner_only(client, user_factory, restaurant_factory):
    _, owner_headers = await user_factory.create_and_login("owner8")
    _, other_headers = await user_factory.create_and_login("intruder2")
    restaurant = await restaurant_factory.create(owner_headers, name="TableTest")

    resp = await client.post(
        f"/api/v1/restaurants/{restaurant['id']}/tables", json={"label": "T1"}, headers=owner_headers
    )
    assert resp.status_code == 200
    table = resp.json()
    assert table["label"] == "T1"
    assert "qr_token" in table
    assert table["restaurant_id"] == restaurant["id"]

    resp = await client.post(
        f"/api/v1/restaurants/{restaurant['id']}/tables", json={"label": "T2"}, headers=other_headers
    )
    assert resp.status_code == 403


async def test_list_tables_owner_only(client, user_factory, restaurant_factory):
    _, owner_headers = await user_factory.create_and_login("owner9")
    _, other_headers = await user_factory.create_and_login("intruder3")
    restaurant = await restaurant_factory.create(owner_headers, name="TableListTest")
    await restaurant_factory.add_table(owner_headers, restaurant["id"], label="T1")
    await restaurant_factory.add_table(owner_headers, restaurant["id"], label="T2")

    resp = await client.get(f"/api/v1/restaurants/{restaurant['id']}/tables", headers=owner_headers)
    assert resp.status_code == 200
    labels = {t["label"] for t in resp.json()}
    assert labels == {"T1", "T2"}

    resp = await client.get(f"/api/v1/restaurants/{restaurant['id']}/tables", headers=other_headers)
    assert resp.status_code == 403


async def test_get_restaurant_orders_owner_only(client, user_factory, restaurant_factory, session_factory):
    _, owner_headers = await user_factory.create_and_login("owner10")
    _, other_headers = await user_factory.create_and_login("intruder4")
    restaurant = await restaurant_factory.create(owner_headers, name="OrdersDash")

    resp = await client.get(f"/api/v1/restaurants/{restaurant['id']}/orders", headers=owner_headers)
    assert resp.status_code == 200
    assert resp.json() == []

    resp = await client.get(f"/api/v1/restaurants/{restaurant['id']}/orders", headers=other_headers)
    assert resp.status_code == 403


async def test_get_restaurant_orders_not_found(client, user_factory):
    _, headers = await user_factory.create_and_login("owner11")
    resp = await client.get("/api/v1/restaurants/99999/orders", headers=headers)
    assert resp.status_code == 404
