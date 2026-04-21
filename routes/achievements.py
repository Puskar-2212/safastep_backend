from fastapi import APIRouter, HTTPException
from database import achievements_collection, user_achievements_collection, users_collection, notifications_collection
from datetime import datetime
import logging
import time

logger = logging.getLogger(__name__)

router = APIRouter()

# Achievement definitions (could be moved to a config or seeded)
ACHIEVEMENTS = [
    {
        "id": "eco_starter",
        "name": "Eco Starter",
        "description": "Earn 200 eco points",
        "iconUrl": "/assets/badges/eco_starter.svg",
        "condition": {"type": "eco_points", "value": 200}
    },
    {
        "id": "eco_enthusiast",
        "name": "Eco Enthusiast",
        "description": "Earn 500 eco points",
        "iconUrl": "/assets/badges/eco_enthusiast.svg",
        "condition": {"type": "eco_points", "value": 500}
    },
    {
        "id": "eco_champion",
        "name": "Eco Champion",
        "description": "Earn 1000 eco points",
        "iconUrl": "/assets/badges/eco_champion.svg",
        "condition": {"type": "eco_points", "value": 1000}
    },
    {
        "id": "first_step",
        "name": "First Step",
        "description": "Create your first post",
        "iconUrl": "/assets/badges/first_step.svg",
        "condition": {"type": "posts", "value": 1}
    },
    {
        "id": "eco_contributor",
        "name": "Eco Contributor",
        "description": "Create 10 posts",
        "iconUrl": "/assets/badges/eco_contributor.svg",
        "condition": {"type": "posts", "value": 10}
    },
    {
        "id": "eco_influencer",
        "name": "Eco Influencer",
        "description": "Create 50 posts",
        "iconUrl": "/assets/badges/eco_influencer.svg",
        "condition": {"type": "posts", "value": 50}
    }
]

@router.get("/achievements")
async def get_all_achievements():
    """Get all possible achievements"""
    return {
        "success": True,
        "achievements": ACHIEVEMENTS
    }

@router.get("/user/{mobile}/achievements")
async def get_user_achievements(mobile: str):
    """Get user's unlocked achievements"""
    # Support both mobile and email identifiers
    user_achievements = list(user_achievements_collection.find({
        "$or": [
            {"mobile": mobile},
            {"email": mobile}
        ]
    }))
    
    # Get all achievements and mark unlocked ones
    all_achievements = []
    for achievement in ACHIEVEMENTS:
        unlocked = any(ua["achievementId"] == achievement["id"] for ua in user_achievements)
        achievement_data = achievement.copy()
        achievement_data["unlocked"] = unlocked
        if unlocked:
            ua = next(ua for ua in user_achievements if ua["achievementId"] == achievement["id"])
            achievement_data["unlockedAt"] = ua["unlockedAt"]
        all_achievements.append(achievement_data)
    
    return {
        "success": True,
        "achievements": all_achievements
    }

@router.post("/user/{mobile}/check-achievements")
async def check_and_award_achievements(mobile: str):
    """Check if user has unlocked any new achievements"""
    # Get user data - support both mobile and email
    user = users_collection.find_one({
        "$or": [
            {"mobile": mobile},
            {"email": mobile}
        ]
    })
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Determine the identifier field to use
    identifier_field = "mobile" if user.get("mobile") else "email"
    identifier_value = user.get("mobile") or user.get("email")
    
    # Get user's current achievements
    user_achievements = list(user_achievements_collection.find({
        "$or": [
            {"mobile": identifier_value},
            {"email": identifier_value}
        ]
    }))
    unlocked_ids = {ua["achievementId"] for ua in user_achievements}
    
    # Check each achievement
    new_unlocks = []
    for achievement in ACHIEVEMENTS:
        if achievement["id"] in unlocked_ids:
            continue
        
        condition = achievement["condition"]
        unlocked = False
        
        if condition["type"] == "eco_points":
            user_eco_points = user.get("ecoPoints", 0)
            if user_eco_points >= condition["value"]:
                unlocked = True
        elif condition["type"] == "posts":
            # Count user's posts - support both mobile and email
            from database import posts_collection
            post_count = posts_collection.count_documents({"identifier": identifier_value})
            if post_count >= condition["value"]:
                unlocked = True
        
        if unlocked:
            # Award achievement using the correct identifier field
            user_achievements_collection.insert_one({
                identifier_field: identifier_value,
                "achievementId": achievement["id"],
                "unlockedAt": datetime.utcnow()
            })
            new_unlocks.append(achievement)
            
            # Create notification for achievement unlock
            try:
                notification = {
                    "userId": identifier_value,
                    "type": "achievement",
                    "title": "🏆 Achievement Unlocked!",
                    "message": f"You've earned the '{achievement['name']}' badge! {achievement['description']}",
                    "read": False,
                    "createdAt": int(time.time()),
                    "data": {
                        "achievementId": achievement["id"],
                        "achievementName": achievement["name"]
                    }
                }
                notifications_collection.insert_one(notification)
                logger.info(f"Created achievement notification for {identifier_value}: {achievement['name']}")
            except Exception as e:
                logger.error(f"Failed to create achievement notification: {e}")
    
    return {
        "success": True,
        "newUnlocks": new_unlocks
    }