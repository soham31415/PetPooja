from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from app.models.order import Order, OrderItem, OrderStatus
from app.models.session import DiningSession, SessionStatus
from app.models.restaurant import MenuItem
from app.services.session_service import is_active_participant
import uuid
from typing import List


async def _validate_order_item(db: AsyncSession, session: DiningSession, item_data: dict) -> None:
    """Validate that an order item is placeable within the given session."""
    menu_item = await db.get(MenuItem, item_data["menu_item_id"])
    if not menu_item:
        raise ValueError(f"Menu item {item_data['menu_item_id']} not found")

    if not session.restaurant_id:
        raise ValueError("Session has no restaurant selected; cannot place orders")

    if menu_item.restaurant_id != session.restaurant_id:
        raise ValueError(
            f"Menu item {item_data['menu_item_id']} does not belong to the session's restaurant"
        )

    assigned_user_id = item_data.get("assigned_user_id")
    if assigned_user_id is not None:
        if not await is_active_participant(db, session.id, assigned_user_id):
            raise ValueError("assigned_user_id must be an active participant of the session")


async def create_order(
    db: AsyncSession,
    session_id: uuid.UUID,
    items: List[dict],
    user_id: uuid.UUID,
) -> Order:
    """
    Create a new order for a dining session.
    items: list of dicts with keys: menu_item_id, quantity, assigned_user_id (optional)
    """
    # Verify session exists and is active
    session = await db.get(DiningSession, session_id)
    if not session:
        raise ValueError("Session not found")
    if session.status != SessionStatus.ACTIVE:
        raise ValueError("Session is not active")

    if not await is_active_participant(db, session_id, user_id):
        raise PermissionError("Must be an active participant of the session to place orders")

    for item_data in items:
        await _validate_order_item(db, session, item_data)

    # Create order
    order = Order(session_id=session_id, status=OrderStatus.PENDING)
    db.add(order)
    await db.flush()  # Get the order ID without committing

    # Create order items
    for item_data in items:
        order_item = OrderItem(
            order_id=order.id,
            menu_item_id=item_data["menu_item_id"],
            quantity=item_data.get("quantity", 1),
            assigned_user_id=item_data.get("assigned_user_id"),
        )
        db.add(order_item)

    await db.commit()

    # Reload with relationships
    return await get_order(db, order.id)


async def get_order(db: AsyncSession, order_id: int) -> Order:
    """Fetch an order with its items and their menu item details."""
    result = await db.execute(
        select(Order)
        .options(selectinload(Order.items).selectinload(OrderItem.menu_item))
        .where(Order.id == order_id)
    )
    order = result.scalars().first()
    if not order:
        raise ValueError("Order not found")
    return order


async def get_orders_for_session(
    db: AsyncSession, session_id: uuid.UUID
) -> List[Order]:
    """List all orders for a dining session."""
    result = await db.execute(
        select(Order)
        .options(selectinload(Order.items).selectinload(OrderItem.menu_item))
        .where(Order.session_id == session_id)
    )
    return result.scalars().all()


# Valid status transitions
_VALID_TRANSITIONS = {
    OrderStatus.PENDING: [OrderStatus.CONFIRMED],
    OrderStatus.CONFIRMED: [OrderStatus.PAID],
    OrderStatus.PAID: [],
}


async def update_order_status(
    db: AsyncSession, order_id: int, new_status: OrderStatus, user_id: uuid.UUID
) -> Order:
    """Update the status of an order with transition validation. Host-only."""
    order = await get_order(db, order_id)

    session = await db.get(DiningSession, order.session_id)
    if not session or session.host_id != user_id:
        raise PermissionError("Only the session host can update order status")

    if new_status not in _VALID_TRANSITIONS.get(order.status, []):
        raise ValueError(
            f"Cannot transition from '{order.status.value}' to '{new_status.value}'"
        )

    order.status = new_status
    db.add(order)
    await db.commit()
    return await get_order(db, order_id)


async def add_item_to_order(
    db: AsyncSession, order_id: int, item_data: dict, user_id: uuid.UUID
) -> Order:
    """Add an item to an existing order (only if pending)."""
    order = await get_order(db, order_id)
    if order.status != OrderStatus.PENDING:
        raise ValueError("Can only add items to pending orders")

    session = await db.get(DiningSession, order.session_id)
    if not await is_active_participant(db, session.id, user_id):
        raise PermissionError("Must be an active participant of the session to modify orders")

    await _validate_order_item(db, session, item_data)

    order_item = OrderItem(
        order_id=order_id,
        menu_item_id=item_data["menu_item_id"],
        quantity=item_data.get("quantity", 1),
        assigned_user_id=item_data.get("assigned_user_id"),
    )
    db.add(order_item)
    await db.commit()
    return await get_order(db, order_id)


async def remove_item_from_order(
    db: AsyncSession, order_id: int, item_id: int, user_id: uuid.UUID
) -> Order:
    """Remove an item from an order (only if pending)."""
    order = await get_order(db, order_id)
    if order.status != OrderStatus.PENDING:
        raise ValueError("Can only remove items from pending orders")

    if not await is_active_participant(db, order.session_id, user_id):
        raise PermissionError("Must be an active participant of the session to modify orders")

    result = await db.execute(
        select(OrderItem).where(
            OrderItem.id == item_id, OrderItem.order_id == order_id
        )
    )
    order_item = result.scalars().first()
    if not order_item:
        raise ValueError("Order item not found in this order")

    await db.delete(order_item)
    await db.commit()
    return await get_order(db, order_id)
