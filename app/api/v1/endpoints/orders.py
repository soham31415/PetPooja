from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import List
import uuid

from app.api import deps
from app.models.order import OrderStatus
from app.models.user import User
from app.schemas.order import OrderCreate, OrderRead, OrderItemCreate, OrderItemAssign
from app.services import order_service

router = APIRouter()


class OrderStatusUpdate(BaseModel):
    status: OrderStatus


@router.post("/", response_model=OrderRead)
async def create_order(
    order_in: OrderCreate,
    current_user: User = Depends(deps.get_current_user),
    db: AsyncSession = Depends(deps.get_db),
):
    """
    Create a new order for a dining session. The caller must be an
    active participant of the session.
    """
    try:
        items = [item.model_dump() for item in order_in.items]
        order = await order_service.create_order(
            db=db, session_id=order_in.session_id, items=items, user_id=current_user.id
        )
        return order
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{order_id}", response_model=OrderRead)
async def get_order(order_id: int, db: AsyncSession = Depends(deps.get_db)):
    """
    Get order details with items.
    """
    try:
        return await order_service.get_order(db=db, order_id=order_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/session/{session_id}", response_model=List[OrderRead])
async def get_orders_for_session(
    session_id: uuid.UUID, db: AsyncSession = Depends(deps.get_db)
):
    """
    List all orders for a dining session.
    """
    return await order_service.get_orders_for_session(db=db, session_id=session_id)


@router.patch("/{order_id}/status", response_model=OrderRead)
async def update_order_status(
    order_id: int,
    status_in: OrderStatusUpdate,
    current_user: User = Depends(deps.get_current_user),
    db: AsyncSession = Depends(deps.get_db),
):
    """
    Update order status. Valid transitions: pending → confirmed → paid.
    Only the session host may update order status.
    """
    try:
        return await order_service.update_order_status(
            db=db, order_id=order_id, new_status=status_in.status, user_id=current_user.id
        )
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{order_id}/items", response_model=OrderRead)
async def add_item_to_order(
    order_id: int,
    item_in: OrderItemCreate,
    current_user: User = Depends(deps.get_current_user),
    db: AsyncSession = Depends(deps.get_db),
):
    """
    Add an item to an existing order. Only works for pending orders,
    and the caller must be an active participant of the session.
    """
    try:
        return await order_service.add_item_to_order(
            db=db, order_id=order_id, item_data=item_in.model_dump(), user_id=current_user.id
        )
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.patch("/{order_id}/items/{item_id}/assign", response_model=OrderRead)
async def assign_order_item(
    order_id: int,
    item_id: int,
    assign_in: OrderItemAssign,
    current_user: User = Depends(deps.get_current_user),
    db: AsyncSession = Depends(deps.get_db),
):
    """
    Reassign an order item to a participant (or back to the shared pool by
    passing `assigned_user_id: null`). Only works for pending orders.
    """
    try:
        return await order_service.update_item_assignment(
            db=db,
            order_id=order_id,
            item_id=item_id,
            assigned_user_id=assign_in.assigned_user_id,
            user_id=current_user.id,
        )
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{order_id}/items/{item_id}", response_model=OrderRead)
async def remove_item_from_order(
    order_id: int,
    item_id: int,
    current_user: User = Depends(deps.get_current_user),
    db: AsyncSession = Depends(deps.get_db),
):
    """
    Remove an item from an order. Only works for pending orders,
    and the caller must be an active participant of the session.
    """
    try:
        return await order_service.remove_item_from_order(
            db=db, order_id=order_id, item_id=item_id, user_id=current_user.id
        )
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
