from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from app.models.session import DiningSession, SessionParticipant
from app.models.user import User
from app.models.restaurant import MenuItem, Restaurant
import uuid
from typing import List, Dict, Any

async def generate_recommendations(db: AsyncSession, session_id: uuid.UUID) -> List[MenuItem]:
    """
    Generate food recommendations for a session.
    Algorithm:
    1. Fetch all participants and their taste profiles.
    2. Aggregate dietary restrictions (Strict filter).
    3. Aggregate preferences (Scoring).
    4. Fetch menu items.
    5. Filter and Score items.
    6. Return sorted list.
    """
    
    # 1. Fetch Session and Participants with Taste Profiles
    # We need to join SessionParticipant -> User -> TasteProfile
    result = await db.execute(
        select(User)
        .join(SessionParticipant)
        .options(selectinload(User.taste_profile))
        .where(
            SessionParticipant.session_id == session_id,
            SessionParticipant.is_active == True
        )
    )
    participants = result.scalars().all()
    
    if not participants:
        return []

    # Get Restaurant ID from Session
    session_result = await db.get(DiningSession, session_id)
    if not session_result:
        return []
    restaurant_id = session_result.restaurant_id
    
    # 2. Aggregate Data
    all_restrictions = set()
    all_preferences = [] # List to allow weighting by frequency
    
    for user in participants:
        if user.taste_profile:
            # Add restrictions
            if user.taste_profile.dietary_restrictions:
                # Handle JSON list or string
                restrictions = user.taste_profile.dietary_restrictions
                if isinstance(restrictions, list):
                    all_restrictions.update(restrictions)
            
            # Add preferences
            if user.taste_profile.preferences:
                prefs = user.taste_profile.preferences
                if isinstance(prefs, list):
                    all_preferences.extend(prefs)

    # 3. Fetch Menu Items
    menu_result = await db.execute(
        select(MenuItem).where(MenuItem.restaurant_id == restaurant_id)
    )
    menu_items = menu_result.scalars().all()
    
    # 4. Filter and Score
    scored_items = []
    
    for item in menu_items:
        # Check Restrictions
        # Logic: If 'Vegetarian' is in restrictions, item MUST have 'Vegetarian' tag
        # This assumes tags are used for restrictions too.
        allowed = True
        item_tags = set(item.tags) if item.tags else set()
        
        # Normalize tags to lowercase for comparison
        item_tags_lower = {t.lower() for t in item_tags}
        
        for restriction in all_restrictions:
            res_lower = restriction.lower()
            # Any dietary restriction held by a participant must be matched
            # by a corresponding tag on the item (e.g. "halal" -> tagged "halal").
            if res_lower not in item_tags_lower:
                allowed = False
                break
        
        if not allowed:
            continue
            
        # Calculate Score
        score = 0
        for pref in all_preferences:
            if pref.lower() in item_tags_lower:
                score += 1
        
        scored_items.append({"item": item, "score": score})
    
    # 5. Sort by Score Descending
    scored_items.sort(key=lambda x: x["score"], reverse=True)
    
    return [x["item"] for x in scored_items]
