from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from app.api import deps
from app.core.security import decode_access_token
from app.core.ws_manager import restaurant_ws_manager
from app.models.restaurant import Restaurant, MenuItem
from app.models.user import User
from app.schemas.restaurant import RestaurantCreate, RestaurantRead, MenuItemCreate, MenuItemRead
from app.schemas.order import OrderRead
from app.services import order_service
from typing import List
import uuid

router = APIRouter()


async def _get_owned_restaurant(db: AsyncSession, restaurant_id: int, user: User) -> Restaurant:
    restaurant = await db.get(Restaurant, restaurant_id)
    if not restaurant:
        raise HTTPException(status_code=404, detail="Restaurant not found")
    if restaurant.owner_id != user.id:
        raise HTTPException(status_code=403, detail="Only the restaurant's owner can do this")
    return restaurant


@router.post("/", response_model=RestaurantRead)
async def create_restaurant(
    restaurant_in: RestaurantCreate,
    current_user: User = Depends(deps.get_current_user),
    db: AsyncSession = Depends(deps.get_db),
):
    """
    Create a new restaurant. The creator becomes its owner and is the
    only one who can manage its menu and view its live order dashboard.
    """
    restaurant = Restaurant(
        name=restaurant_in.name,
        address=restaurant_in.address,
        owner_id=current_user.id,
    )
    db.add(restaurant)
    await db.commit()
    await db.refresh(restaurant)

    # Reload with menu_items to prevent MissingGreenlet error
    result = await db.execute(
        select(Restaurant).options(selectinload(Restaurant.menu_items)).where(Restaurant.id == restaurant.id)
    )
    return result.scalars().first()

@router.get("/", response_model=List[RestaurantRead])
async def list_restaurants(skip: int = 0, limit: int = 100, db: AsyncSession = Depends(deps.get_db)):
    """
    List all restaurants.
    """
    result = await db.execute(
        select(Restaurant).options(selectinload(Restaurant.menu_items)).offset(skip).limit(limit)
    )
    return result.scalars().all()

@router.post("/{restaurant_id}/menu", response_model=MenuItemRead)
async def create_menu_item(
    restaurant_id: int,
    item_in: MenuItemCreate,
    current_user: User = Depends(deps.get_current_user),
    db: AsyncSession = Depends(deps.get_db),
):
    """
    Add an item to a restaurant's menu. Only the restaurant's owner may do this.
    """
    await _get_owned_restaurant(db, restaurant_id, current_user)

    menu_item = MenuItem(
        restaurant_id=restaurant_id,
        name=item_in.name,
        description=item_in.description,
        price=item_in.price,
        tags=item_in.tags
    )
    db.add(menu_item)
    await db.commit()
    await db.refresh(menu_item)
    return menu_item

@router.get("/{restaurant_id}/menu", response_model=List[MenuItemRead])
async def list_menu_items(restaurant_id: int, db: AsyncSession = Depends(deps.get_db)):
    """
    Get the menu for a specific restaurant.
    """
    # Verify restaurant exists
    restaurant = await db.get(Restaurant, restaurant_id)
    if not restaurant:
        raise HTTPException(status_code=404, detail="Restaurant not found")

    result = await db.execute(select(MenuItem).where(MenuItem.restaurant_id == restaurant_id))
    return result.scalars().all()


@router.get("/{restaurant_id}/orders", response_model=List[OrderRead])
async def get_restaurant_orders(
    restaurant_id: int,
    current_user: User = Depends(deps.get_current_user),
    db: AsyncSession = Depends(deps.get_db),
):
    """
    Live order dashboard: every order placed at this restaurant, across
    all dining sessions, newest first. Owner only.
    """
    await _get_owned_restaurant(db, restaurant_id, current_user)
    return await order_service.get_orders_for_restaurant(db=db, restaurant_id=restaurant_id)


@router.websocket("/{restaurant_id}/ws/orders")
async def restaurant_orders_feed(
    websocket: WebSocket,
    restaurant_id: int,
    token: str,
    db: AsyncSession = Depends(deps.get_db),
):
    """
    Live feed of order events ("order_created", "order_status_updated",
    "order_item_added", "order_item_removed") for a restaurant's dashboard.

    Browsers can't set Authorization headers on WebSocket connections, so
    authenticate by passing the JWT access token as a `token` query param,
    e.g. `wss://.../restaurants/{id}/ws/orders?token=<jwt>`. Only the
    restaurant's owner may connect; the connection is closed otherwise.
    """
    payload = decode_access_token(token)
    if payload is None:
        await websocket.close(code=4401)
        return

    try:
        user_id = uuid.UUID(payload.get("sub"))
    except (TypeError, ValueError):
        await websocket.close(code=4401)
        return

    restaurant = await db.get(Restaurant, restaurant_id)
    if not restaurant or restaurant.owner_id != user_id:
        await websocket.close(code=4403)
        return

    await restaurant_ws_manager.connect(restaurant_id, websocket)
    try:
        while True:
            # Clients don't need to send anything; just keep the socket open
            # and detect disconnects.
            await websocket.receive_text()
    except WebSocketDisconnect:
        await restaurant_ws_manager.disconnect(restaurant_id, websocket)
