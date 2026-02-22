from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from app.api import deps
from app.models.user import User, TasteProfile
from app.schemas.user import (
    UserCreate, UserRead, GuestCreate, TasteProfileCreate,
    LoginRequest, Token,
)
from app.core.security import hash_password, verify_password, create_access_token
import uuid

router = APIRouter()

@router.post("/", response_model=UserRead)
async def create_user(user_in: UserCreate, db: AsyncSession = Depends(deps.get_db)):
    """
    Create a new registered user (with password).
    """
    # Check if username exists
    result = await db.execute(select(User).where(User.username == user_in.username))
    if result.scalars().first():
        raise HTTPException(status_code=400, detail="Username already taken")

    # Create User with hashed password
    new_user = User(
        username=user_in.username,
        hashed_password=hash_password(user_in.password),
        is_guest=False,
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    
    # Initialize empty taste profile
    profile = TasteProfile(user_id=new_user.id)
    db.add(profile)
    await db.commit()
    
    # Reload user with taste profile
    result = await db.execute(
        select(User).options(selectinload(User.taste_profile)).where(User.id == new_user.id)
    )
    return result.scalars().first()

@router.post("/login", response_model=Token)
async def login(login_in: LoginRequest, db: AsyncSession = Depends(deps.get_db)):
    """
    Authenticate a registered user and return a JWT token.
    """
    result = await db.execute(select(User).where(User.username == login_in.username))
    user = result.scalars().first()

    if not user or not user.hashed_password:
        raise HTTPException(status_code=401, detail="Invalid username or password")

    if not verify_password(login_in.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid username or password")

    access_token = create_access_token(data={"sub": str(user.id)})
    return Token(access_token=access_token)

@router.post("/guest", response_model=UserRead)
async def create_guest(guest_in: GuestCreate, db: AsyncSession = Depends(deps.get_db)):
    """
    Create a guest user (no login required).
    """
    new_guest = User(username=guest_in.username, is_guest=True)
    db.add(new_guest)
    await db.commit()
    await db.refresh(new_guest)

    # Create Taste Profile (optional data from input)
    profile_data = guest_in.taste_profile or TasteProfileCreate()
    
    profile = TasteProfile(
        user_id=new_guest.id,
        preferences=profile_data.preferences,
        daringness=profile_data.daringness,
        dietary_restrictions=profile_data.dietary_restrictions
    )
    db.add(profile)
    await db.commit()
    
    # Reload user with taste profile
    result = await db.execute(
        select(User).options(selectinload(User.taste_profile)).where(User.id == new_guest.id)
    )
    return result.scalars().first()

@router.get("/me", response_model=UserRead)
async def read_current_user(
    current_user: User = Depends(deps.get_current_user),
    db: AsyncSession = Depends(deps.get_db),
):
    """
    Get the currently authenticated user's details.
    """
    result = await db.execute(
        select(User).options(selectinload(User.taste_profile)).where(User.id == current_user.id)
    )
    return result.scalars().first()

@router.get("/{user_id}", response_model=UserRead)
async def read_user(user_id: uuid.UUID, db: AsyncSession = Depends(deps.get_db)):
    """
    Get user details by ID.
    """
    result = await db.execute(
        select(User).options(selectinload(User.taste_profile)).where(User.id == user_id)
    )
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@router.put("/{user_id}/taste_profile", response_model=UserRead)
async def update_taste_profile(
    user_id: uuid.UUID, 
    profile_in: TasteProfileCreate, 
    db: AsyncSession = Depends(deps.get_db)
):
    """
    Update a user's taste profile.
    """
    result = await db.execute(select(TasteProfile).where(TasteProfile.user_id == user_id))
    profile = result.scalars().first()
    
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    profile.preferences = profile_in.preferences
    profile.daringness = profile_in.daringness
    profile.dietary_restrictions = profile_in.dietary_restrictions
    
    db.add(profile)
    await db.commit()
    
    # Return updated user
    result = await db.execute(
        select(User).options(selectinload(User.taste_profile)).where(User.id == user_id)
    )
    return result.scalars().first()
