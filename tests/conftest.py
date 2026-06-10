import os
import uuid

# --- Ensure required settings env vars are present BEFORE app.core.config is imported ---
os.environ.setdefault("PROJECT_NAME", "PetPooja")
os.environ.setdefault("API_V1_STR", "/api/v1")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("POSTGRES_USER", "postgres")
os.environ.setdefault("POSTGRES_PASSWORD", "postgres")
os.environ.setdefault("POSTGRES_SERVER", "localhost")
os.environ.setdefault("POSTGRES_PORT", "5432")
os.environ.setdefault("POSTGRES_DB", "petpooja_test")
os.environ.setdefault("SECRET_KEY", "test-secret-key")
os.environ.setdefault("ALGORITHM", "HS256")
os.environ.setdefault("ACCESS_TOKEN_EXPIRE_MINUTES", "60")

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.api import deps
from app.db.base_class import Base

# Import all models so they're registered on Base.metadata
from app.models import (  # noqa: F401
    User, TasteProfile,
    DiningSession, SessionParticipant, SessionStatus,
    Restaurant, MenuItem,
    Order, OrderItem, OrderStatus,
)
from app.models.restaurant import RestaurantTable  # noqa: F401

from app.core.security import hash_password, create_access_token


# --- Test database engine (in-memory SQLite, shared across connections via StaticPool) ---
test_engine = create_async_engine(
    "sqlite+aiosqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
    future=True,
)

TestSessionLocal = async_sessionmaker(
    test_engine, class_=AsyncSession, expire_on_commit=False
)


async def _override_get_db():
    async with TestSessionLocal() as session:
        yield session


app.dependency_overrides[deps.get_db] = _override_get_db


@pytest_asyncio.fixture(autouse=True)
async def _setup_db():
    """Create a fresh set of tables before each test, and drop them after."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture
async def db_session():
    async with TestSessionLocal() as session:
        yield session


# ---------------------------------------------------------------------------
# Factory helpers
# ---------------------------------------------------------------------------

async def _create_user_direct(username: str, password: str = "password123", is_guest: bool = False) -> User:
    async with TestSessionLocal() as session:
        user = User(
            username=username,
            hashed_password=None if is_guest else hash_password(password),
            is_guest=is_guest,
        )
        session.add(user)
        await session.flush()
        profile = TasteProfile(user_id=user.id)
        session.add(profile)
        await session.commit()
        await session.refresh(user)
        return user


def _auth_headers(user_id: uuid.UUID) -> dict:
    token = create_access_token(data={"sub": str(user_id)})
    return {"Authorization": f"Bearer {token}"}


class UserFactory:
    """Helper bound to a test client for creating users (and tokens) via the real API."""

    def __init__(self, client: AsyncClient):
        self.client = client

    async def register(self, username: str, password: str = "password123") -> dict:
        resp = await self.client.post(
            "/api/v1/users/", json={"username": username, "password": password}
        )
        assert resp.status_code == 200, resp.text
        return resp.json()

    async def login(self, username: str, password: str = "password123") -> str:
        resp = await self.client.post(
            "/api/v1/users/login", json={"username": username, "password": password}
        )
        assert resp.status_code == 200, resp.text
        return resp.json()["access_token"]

    async def create_and_login(self, username: str, password: str = "password123") -> tuple[dict, dict]:
        """Returns (user_dict, auth_headers)."""
        user = await self.register(username, password)
        token = await self.login(username, password)
        return user, {"Authorization": f"Bearer {token}"}

    async def guest(self, username: str, taste_profile: dict | None = None) -> dict:
        payload = {"username": username}
        if taste_profile is not None:
            payload["taste_profile"] = taste_profile
        resp = await self.client.post("/api/v1/users/guest", json=payload)
        assert resp.status_code == 200, resp.text
        return resp.json()


@pytest.fixture
def user_factory(client):
    return UserFactory(client)


class RestaurantFactory:
    def __init__(self, client: AsyncClient):
        self.client = client

    async def create(self, owner_headers: dict, name: str = "Test Restaurant", address: str = "123 Main St") -> dict:
        resp = await self.client.post(
            "/api/v1/restaurants/",
            json={"name": name, "address": address},
            headers=owner_headers,
        )
        assert resp.status_code == 200, resp.text
        return resp.json()

    async def add_menu_item(
        self,
        owner_headers: dict,
        restaurant_id: int,
        name: str = "Pizza",
        description: str = "Cheesy pizza",
        price: float = 10.0,
        tags: list[str] | None = None,
    ) -> dict:
        resp = await self.client.post(
            f"/api/v1/restaurants/{restaurant_id}/menu",
            json={"name": name, "description": description, "price": price, "tags": tags or []},
            headers=owner_headers,
        )
        assert resp.status_code == 200, resp.text
        return resp.json()

    async def add_table(self, owner_headers: dict, restaurant_id: int, label: str = "Table 1") -> dict:
        resp = await self.client.post(
            f"/api/v1/restaurants/{restaurant_id}/tables",
            json={"label": label},
            headers=owner_headers,
        )
        assert resp.status_code == 200, resp.text
        return resp.json()


@pytest.fixture
def restaurant_factory(client):
    return RestaurantFactory(client)


class SessionFactory:
    def __init__(self, client: AsyncClient):
        self.client = client

    async def create(self, host_headers: dict, restaurant_id: int | None = None) -> dict:
        resp = await self.client.post(
            "/api/v1/sessions/",
            json={"restaurant_id": restaurant_id},
            headers=host_headers,
        )
        assert resp.status_code == 200, resp.text
        return resp.json()

    async def join(self, headers: dict, session_id: str) -> dict:
        resp = await self.client.post(f"/api/v1/sessions/{session_id}/join", headers=headers)
        assert resp.status_code == 200, resp.text
        return resp.json()


@pytest.fixture
def session_factory(client):
    return SessionFactory(client)
