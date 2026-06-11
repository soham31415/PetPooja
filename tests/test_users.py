import pytest


async def test_register_user_success(client):
    resp = await client.post("/api/v1/users/", json={"username": "alice", "password": "secret123"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["username"] == "alice"
    assert data["is_guest"] is False
    assert "id" in data
    assert data["taste_profile"] is not None
    assert data["taste_profile"]["preferences"] == []
    assert data["taste_profile"]["daringness"] == 5


async def test_register_duplicate_username(client):
    await client.post("/api/v1/users/", json={"username": "bob", "password": "secret123"})
    resp = await client.post("/api/v1/users/", json={"username": "bob", "password": "other"})
    assert resp.status_code == 400
    assert "already taken" in resp.json()["detail"]


async def test_login_success(client):
    await client.post("/api/v1/users/", json={"username": "carol", "password": "mypassword"})
    resp = await client.post("/api/v1/users/login", json={"username": "carol", "password": "mypassword"})
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


async def test_login_wrong_password(client):
    await client.post("/api/v1/users/", json={"username": "dave", "password": "rightpass"})
    resp = await client.post("/api/v1/users/login", json={"username": "dave", "password": "wrongpass"})
    assert resp.status_code == 401


async def test_login_unknown_user(client):
    resp = await client.post("/api/v1/users/login", json={"username": "ghost", "password": "x"})
    assert resp.status_code == 401


async def test_create_guest(client):
    resp = await client.post("/api/v1/users/guest", json={"username": "guest1"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["username"] == "guest1"
    assert data["is_guest"] is True
    assert data["taste_profile"]["preferences"] == []


async def test_create_guest_with_taste_profile(client):
    resp = await client.post(
        "/api/v1/users/guest",
        json={
            "username": "guest2",
            "taste_profile": {
                "preferences": ["spicy", "vegan"],
                "daringness": 8,
                "dietary_restrictions": ["vegan"],
            },
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["taste_profile"]["preferences"] == ["spicy", "vegan"]
    assert data["taste_profile"]["daringness"] == 8
    assert data["taste_profile"]["dietary_restrictions"] == ["vegan"]


async def test_get_me_requires_auth(client):
    resp = await client.get("/api/v1/users/me")
    assert resp.status_code == 401


async def test_get_me_success(client, user_factory):
    user, headers = await user_factory.create_and_login("erin")
    resp = await client.get("/api/v1/users/me", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["username"] == "erin"
    assert data["id"] == user["id"]


async def test_get_me_invalid_token(client):
    resp = await client.get("/api/v1/users/me", headers={"Authorization": "Bearer not-a-real-token"})
    assert resp.status_code == 401


async def test_get_user_by_id(client, user_factory):
    user, _ = await user_factory.create_and_login("frank")
    resp = await client.get(f"/api/v1/users/{user['id']}")
    assert resp.status_code == 200
    assert resp.json()["username"] == "frank"


async def test_get_user_not_found(client):
    import uuid
    resp = await client.get(f"/api/v1/users/{uuid.uuid4()}")
    assert resp.status_code == 404


async def test_update_taste_profile(client, user_factory):
    user, _ = await user_factory.create_and_login("grace")
    resp = await client.put(
        f"/api/v1/users/{user['id']}/taste_profile",
        json={"preferences": ["sweet"], "daringness": 9, "dietary_restrictions": ["nut-free"]},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["taste_profile"]["preferences"] == ["sweet"]
    assert data["taste_profile"]["daringness"] == 9
    assert data["taste_profile"]["dietary_restrictions"] == ["nut-free"]


async def test_update_taste_profile_not_found(client):
    import uuid
    resp = await client.put(
        f"/api/v1/users/{uuid.uuid4()}/taste_profile",
        json={"preferences": [], "daringness": 5, "dietary_restrictions": []},
    )
    assert resp.status_code == 404
