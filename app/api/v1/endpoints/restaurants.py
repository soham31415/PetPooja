from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from app.api import deps
from app.models.restaurant import Restaurant, MenuItem
from app.schemas.restaurant import RestaurantCreate, RestaurantRead, MenuItemCreate, MenuItemRead
from typing import List

router = APIRouter()

@router.post("/", response_model=RestaurantRead)
async def create_restaurant(restaurant_in: RestaurantCreate, db: AsyncSession = Depends(deps.get_db)):
    """
    Create a new restaurant.
    """
    restaurant = Restaurant(name=restaurant_in.name, address=restaurant_in.address)
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
    db: AsyncSession = Depends(deps.get_db)
):
    """
    Add an item to a restaurant's menu.
    """
    # Verify restaurant exists
    restaurant = await db.get(Restaurant, restaurant_id)
    if not restaurant:
        raise HTTPException(status_code=404, detail="Restaurant not found")

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
