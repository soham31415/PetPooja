from fastapi import APIRouter
from app.api.v1.endpoints import users, restaurants, sessions, orders

api_router = APIRouter()
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(restaurants.router, prefix="/restaurants", tags=["restaurants"])
api_router.include_router(sessions.router, prefix="/sessions", tags=["sessions"])
api_router.include_router(orders.router, prefix="/orders", tags=["orders"])
