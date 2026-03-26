from fastapi import APIRouter, HTTPException, Form, Query, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from database import user_db
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
import pytz
from bson import ObjectId
from pydantic import BaseModel, Field
from enum import Enum
import jwt
import os

router = APIRouter()
security = HTTPBearer()

# JWT Configuration (should match admin_auth.py)
JWT_SECRET = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production")
JWT_ALGORITHM = "HS256"

def verify_admin_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    """Verify admin JWT token"""
    try:
        payload = jwt.decode(credentials.credentials, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return {"username": payload.get("sub"), "role": payload.get("role")}
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

# Get collections
challenges_collection = user_db["challenges"]
user_challenges_collection = user_db["user_challenges"]
users_collection = user_db["user_data"]
notifications_collection = user_db["notifications"]

# Pydantic models for admin endpoints
class DifficultyLevel(str, Enum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"

class ChallengeStatus(str, Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    INACTIVE = "inactive"
    ARCHIVED = "archived"

class ChallengeCreate(BaseModel):
    challenge_id: str = Field(..., pattern="^[a-z0-9_]+$")
    title: str = Field(..., min_length=3, max_length=100)
    description: str = Field(..., min_length=10, max_length=500)
    duration_days: int = Field(..., ge=1, le=365)
    reward_points: int = Field(..., ge=10, le=10000)
    category: str
    icon: str
    difficulty: DifficultyLevel
    tips: List[str] = Field(default_factory=list)
    allow_one_skip: bool = False
    featured: bool = False
    tags: List[str] = Field(default_factory=list)
    admin_notes: Optional[str] = None

class ChallengeUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    duration_days: Optional[int] = None
    reward_points: Optional[int] = None
    difficulty: Optional[DifficultyLevel] = None
    tips: Optional[List[str]] = None
    active: Optional[bool] = None
    featured: Optional[bool] = None
    tags: Optional[List[str]] = None
    admin_notes: Optional[str] = None

class ChallengeStats(BaseModel):
    total_participants: int
    active_participants: int
    completed_participants: int
    completion_rate: float
    avg_streak: float
    total_points_awarded: int
    avg_completion_time: float
    daily_participation: Dict[str, int]

# Helper function to check and deactivate missed challenges
async def check_and_deactivate_missed_challenges():
    """Check for challenges that should be deactivated due to missed days"""
    try:
        today = datetime.now(pytz.UTC).date()
        
        # Find all active challenges
        active_challenges = user_challenges_collection.find({
            "status": "in_progress"
        })
        
        for challenge in active_challenges:
            try:
                user_id = challenge["user_id"]
                challenge_id = challenge["_id"]
                check_ins = challenge.get("check_ins", [])
                allow_one_skip = challenge.get("allow_one_skip", False)
                missed_days = 0
                
                # Count missed days (past dates that weren't checked in)
                for checkin in check_ins:
                    try:
                        checkin_date = datetime.strptime(checkin["date"], "%Y-%m-%d").date()
                        if checkin_date < today and not checkin.get("checked_in", False):
                            missed_days += 1
                    except (ValueError, KeyError) as e:
                        print(f"DEBUG: Error parsing checkin date: {str(e)}")
                        continue
                
                # Deactivate if missed more than allowed
                max_allowed_misses = 1 if allow_one_skip else 0
                if missed_days > max_allowed_misses:
                    # Deactivate the challenge
                    user_challenges_collection.update_one(
                        {"_id": challenge_id},
                        {"$set": {
                            "status": "failed",
                            "failed_at": datetime.now(pytz.UTC),
                            "failure_reason": f"Missed {missed_days} days"
                        }}
                    )
                    
                    # Send notification to user
                    try:
                        notification = {
                            "user_id": user_id,
                            "title": "Challenge Failed",
                            "message": f"Your challenge '{challenge.get('challenge_title', 'Unknown')}' has been deactivated due to missing {missed_days} days.",
                            "type": "challenge_failed",
                            "challenge_id": str(challenge_id),
                            "created_at": datetime.now(pytz.UTC),
                            "read": False
                        }
                        notifications_collection.insert_one(notification)
                    except Exception as e:
                        print(f"DEBUG: Error creating notification: {str(e)}")
                        
            except Exception as e:
                print(f"DEBUG: Error processing challenge {challenge.get('_id', 'unknown')}: {str(e)}")
                continue
                
    except Exception as e:
        print(f"ERROR in check_and_deactivate_missed_challenges: {str(e)}")
        # Don't raise the error, just log it so it doesn't break other functions

# Get all available daily check-in challenges
@router.get("/challenges/daily-checkin")
async def get_daily_checkin_challenges(user_id: str = None):
    try:
        # Check and deactivate missed challenges first
        await check_and_deactivate_missed_challenges()
        
        # Get all active challenges
        all_challenges = list(challenges_collection.find(
            {"type": "daily_checkin", "active": True},
            {"_id": 0}
        ))
        
        print(f"DEBUG: Found {len(all_challenges)} challenges in database")
        print(f"DEBUG: user_id parameter: {user_id}")
        
        # If no user_id provided, return all challenges without cooldown info
        if not user_id:
            print("DEBUG: No user_id provided, returning all challenges")
            for challenge in all_challenges:
                challenge["in_cooldown"] = False
            return {"success": True, "challenges": all_challenges}
        
        print(f"DEBUG: Processing challenges for user_id: {user_id}")
        
        # Filter out challenges that are in cooldown period
        available_challenges = []
        
        for challenge in all_challenges:
            try:
                challenge_id = challenge["challenge_id"]
                print(f"DEBUG: Processing challenge: {challenge_id}")
                
                # Check if user has this challenge currently active (in_progress)
                active_challenge = user_challenges_collection.find_one({
                    "user_id": user_id,
                    "challenge_id": challenge_id,
                    "status": "in_progress"
                })
                
                if active_challenge:
                    print(f"DEBUG: Challenge {challenge_id} is currently active - skipping from available list")
                    continue  # Skip this challenge as it's already active
                
                # Check if user has completed this challenge recently
                recent_completion = user_challenges_collection.find_one({
                    "user_id": user_id,
                    "challenge_id": challenge_id,
                    "status": {"$in": ["completed", "claimed"]},
                    "$or": [
                        {"claimed_at": {"$exists": True}},
                        {"completed_at": {"$exists": True}},
                        {"reward_claimed": True}  # Handle legacy completed challenges
                    ]
                }, sort=[("claimed_at", -1), ("completed_at", -1)])  # Get most recent completion
                
                print(f"DEBUG: Recent completion found: {recent_completion is not None}")
                
                if recent_completion:
                    print(f"DEBUG: Recent completion details - Status: {recent_completion.get('status')}, Completed: {recent_completion.get('completed')}, Reward claimed: {recent_completion.get('reward_claimed')}")
                    
                    # Use claimed_at if available, otherwise use completed_at
                    completion_date = recent_completion.get("claimed_at") or recent_completion.get("completed_at")
                    
                    print(f"DEBUG: Completion date: {completion_date}")
                    
                    if completion_date:
                        try:
                            if isinstance(completion_date, str):
                                completion_date = datetime.fromisoformat(completion_date.replace('Z', '+00:00'))
                            
                            # Ensure both datetimes are timezone-aware for comparison
                            if completion_date.tzinfo is None:
                                completion_date = pytz.UTC.localize(completion_date)
                            
                            current_time = datetime.now(pytz.UTC)
                            days_since_completion = (current_time - completion_date).days
                        
                            print(f"DEBUG: Days since completion: {days_since_completion}")
                            
                            if days_since_completion < 7:
                                # Still in cooldown period, add cooldown info
                                challenge["in_cooldown"] = True
                                challenge["cooldown_days_left"] = 7 - days_since_completion
                                challenge["can_restart_date"] = (completion_date + timedelta(days=7)).strftime("%Y-%m-%d")
                                print(f"DEBUG: Challenge {challenge['challenge_id']} in cooldown for {7 - days_since_completion} days")
                            else:
                                # Cooldown period over, can restart
                                challenge["in_cooldown"] = False
                                print(f"DEBUG: Challenge {challenge['challenge_id']} cooldown expired")
                        except Exception as datetime_error:
                            print(f"DEBUG: Error processing datetime for challenge {challenge['challenge_id']}: {str(datetime_error)}")
                            # If there's a datetime error, assume no cooldown
                            challenge["in_cooldown"] = False
                    else:
                        # No completion date found
                        challenge["in_cooldown"] = False
                        print(f"DEBUG: Challenge {challenge['challenge_id']} no completion date")
                else:
                    # Never completed or no recent completion
                    challenge["in_cooldown"] = False
                    print(f"DEBUG: Challenge {challenge['challenge_id']} never completed")
                
                available_challenges.append(challenge)
                
            except Exception as e:
                print(f"DEBUG: Error processing challenge {challenge.get('challenge_id', 'unknown')}: {str(e)}")
                # If there's an error processing this challenge, add it without cooldown info
                challenge["in_cooldown"] = False
                available_challenges.append(challenge)
        
        print(f"DEBUG: Returning {len(available_challenges)} challenges")
        return {"success": True, "challenges": available_challenges}
        
    except Exception as e:
        print(f"ERROR in get_daily_checkin_challenges: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# Accept/Start a challenge
@router.post("/challenges/{challenge_id}/accept")
async def accept_challenge(
    challenge_id: str,
    user_id: str = Form(...)
):
    try:
        print(f"DEBUG: Accepting challenge {challenge_id} for user {user_id}")
        
        # Validate user_id
        if not user_id or user_id.strip() == "":
            raise HTTPException(status_code=400, detail="User ID is required")
        
        # Check if challenge exists
        challenge = challenges_collection.find_one({"challenge_id": challenge_id, "active": True})
        if not challenge:
            raise HTTPException(status_code=404, detail="Challenge not found or inactive")
        
        print(f"DEBUG: Found challenge: {challenge.get('title', 'No title')}")
        
        # Check if user already has this challenge active
        existing_active = user_challenges_collection.find_one({
            "user_id": user_id,
            "challenge_id": challenge_id,
            "status": {"$in": ["in_progress"]}
        })
        
        if existing_active:
            return {"success": False, "message": "You already have this challenge active"}
        
        print("DEBUG: Checking for recent completions...")
        
        # Check if user completed this challenge recently (within 7 days)
        try:
            recent_completion = user_challenges_collection.find_one({
                "user_id": user_id,
                "challenge_id": challenge_id,
                "status": {"$in": ["completed", "claimed"]},
                "$or": [
                    {"claimed_at": {"$exists": True}},
                    {"completed_at": {"$exists": True}},
                    {"reward_claimed": True}  # Handle legacy completed challenges
                ]
            }, sort=[("claimed_at", -1), ("completed_at", -1)])  # Get most recent completion
            
            if recent_completion:
                # Use claimed_at if available, otherwise use completed_at
                completion_date = recent_completion.get("claimed_at") or recent_completion.get("completed_at")
                
                if completion_date:
                    try:
                        if isinstance(completion_date, str):
                            completion_date = datetime.fromisoformat(completion_date.replace('Z', '+00:00'))
                        
                        # Ensure both datetimes are timezone-aware for comparison
                        if completion_date.tzinfo is None:
                            completion_date = pytz.UTC.localize(completion_date)
                        
                        current_time = datetime.now(pytz.UTC)
                        days_since_completion = (current_time - completion_date).days
                        
                        print(f"DEBUG: Challenge last completed/claimed {days_since_completion} days ago")
                        
                        if days_since_completion < 7:
                            days_left = 7 - days_since_completion
                            return {
                                "success": False, 
                                "message": f"You can restart this challenge in {days_left} day{'s' if days_left != 1 else ''}. Completed challenges have a 7-day cooldown period."
                            }
                    except Exception as datetime_error:
                        print(f"DEBUG: Error processing datetime in accept challenge: {str(datetime_error)}")
                        # Continue anyway if there's an error checking completions
        except Exception as e:
            print(f"DEBUG: Error checking recent completions: {str(e)}")
            # Continue anyway if there's an error checking completions
        
        print("DEBUG: Creating check-ins array...")
        
        # Create check-ins array starting from today with real calendar dates
        check_ins = []
        start_date = datetime.now(pytz.UTC).date()
        
        for day in range(challenge["duration_days"]):
            current_date = start_date + timedelta(days=day)
            check_ins.append({
                "day": day + 1,
                "date": current_date.strftime("%Y-%m-%d"),
                "checked_in": False,
                "timestamp": None,
                "note": None
            })
        
        print(f"DEBUG: Created {len(check_ins)} check-ins")
        
        # Create user challenge
        user_challenge = {
            "user_id": user_id,
            "challenge_id": challenge_id,
            "challenge_title": challenge["title"],
            "challenge_icon": challenge.get("icon", "🎯"),
            "challenge_category": challenge.get("category", "general"),
            "status": "in_progress",
            "started_at": datetime.now(pytz.UTC),
            "target_days": challenge["duration_days"],
            "current_streak": 0,
            "check_ins": check_ins,
            "completed": False,
            "completed_at": None,
            "reward_points": challenge["reward_points"],
            "reward_claimed": False,
            "missed_days": 0,
            "allow_one_skip": challenge.get("allow_one_skip", False)
        }
        
        print("DEBUG: Inserting user challenge...")
        
        result = user_challenges_collection.insert_one(user_challenge)
        user_challenge["_id"] = str(result.inserted_id)
        
        print(f"DEBUG: Successfully created challenge with ID: {user_challenge['_id']}")
        
        return {
            "success": True,
            "message": "Challenge accepted!",
            "user_challenge": user_challenge
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"ERROR in accept_challenge: {str(e)}")
        import traceback
        print(f"TRACEBACK: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Error accepting challenge: {str(e)}")


# Daily check-in
@router.post("/challenges/{user_challenge_id}/checkin")
async def daily_checkin(
    user_challenge_id: str,
    user_id: str = Form(...),
    note: Optional[str] = Form(None)
):
    try:
        # Validate inputs
        if not user_id or user_id.strip() == "":
            raise HTTPException(status_code=400, detail="User ID is required")
        
        if not ObjectId.is_valid(user_challenge_id):
            raise HTTPException(status_code=400, detail="Invalid challenge ID format")
        
        # Get user challenge
        user_challenge = user_challenges_collection.find_one({
            "_id": ObjectId(user_challenge_id),
            "user_id": user_id
        })
        
        if not user_challenge:
            raise HTTPException(status_code=404, detail="Challenge not found or doesn't belong to you")
        
        if user_challenge["status"] not in ["in_progress"]:
            return {"success": False, "message": "Challenge is not active"}
        
        # Get today's date
        today = datetime.now(pytz.UTC).date().strftime("%Y-%m-%d")
        
        # Find today's check-in
        check_ins = user_challenge["check_ins"]
        today_checkin = None
        today_index = None
        
        for i, checkin in enumerate(check_ins):
            if checkin["date"] == today:
                today_checkin = checkin
                today_index = i
                break
        
        if not today_checkin:
            return {"success": False, "message": "No check-in available for today. You may have missed the window."}
        
        if today_checkin["checked_in"]:
            return {"success": False, "message": "Already checked in today"}
        
        # Update check-in
        check_ins[today_index]["checked_in"] = True
        check_ins[today_index]["timestamp"] = datetime.now(pytz.UTC)
        check_ins[today_index]["note"] = note if note and note.strip() else None
        
        # Calculate current streak and missed days
        current_streak = 0
        missed_days = 0
        today_date = datetime.now(pytz.UTC).date()
        
        for checkin in check_ins:
            checkin_date = datetime.strptime(checkin["date"], "%Y-%m-%d").date()
            if checkin_date <= today_date:  # Only count up to today
                if checkin["checked_in"]:
                    current_streak += 1
                elif checkin_date < today_date:  # Past dates that weren't checked in
                    missed_days += 1
        
        # Check if challenge is completed
        completed = all(c["checked_in"] for c in check_ins)
        
        # Update user challenge
        update_data = {
            "check_ins": check_ins,
            "current_streak": current_streak,
            "completed": completed,
            "missed_days": missed_days
        }
        
        if completed:
            update_data["completed_at"] = datetime.now(pytz.UTC)
            update_data["status"] = "completed"
        
        user_challenges_collection.update_one(
            {"_id": ObjectId(user_challenge_id)},
            {"$set": update_data}
        )
        
        response = {
            "success": True,
            "message": "Checked in successfully! 🎉",
            "current_streak": current_streak,
            "completed": completed,
            "missed_days": missed_days
        }
        
        if completed:
            response["message"] = "🎉 Challenge completed! Claim your reward!"
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error checking in: {str(e)}")


# Get user's active challenges
@router.get("/challenges/my-challenges")
async def get_my_challenges(user_id: str):
    try:
        # Validate user_id
        if not user_id or user_id.strip() == "":
            raise HTTPException(status_code=400, detail="User ID is required")
        
        # Check and deactivate missed challenges first
        await check_and_deactivate_missed_challenges()
        
        challenges = list(user_challenges_collection.find(
            {"user_id": user_id, "status": {"$in": ["in_progress", "completed", "claimed", "failed"]}}
        ).sort("started_at", -1))  # Sort by most recent first
        
        # Convert ObjectId to string and handle datetime serialization
        for challenge in challenges:
            challenge["_id"] = str(challenge["_id"])
            if "started_at" in challenge and challenge["started_at"]:
                challenge["started_at"] = challenge["started_at"].isoformat()
            if "completed_at" in challenge and challenge["completed_at"]:
                challenge["completed_at"] = challenge["completed_at"].isoformat()
            if "failed_at" in challenge and challenge["failed_at"]:
                challenge["failed_at"] = challenge["failed_at"].isoformat()
            if "check_ins" in challenge:
                for checkin in challenge["check_ins"]:
                    if checkin.get("timestamp") and checkin["timestamp"]:
                        checkin["timestamp"] = checkin["timestamp"].isoformat()
        
        return {"success": True, "challenges": challenges}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching challenges: {str(e)}")


# Claim reward
@router.post("/challenges/{user_challenge_id}/claim-reward")
async def claim_reward(
    user_challenge_id: str,
    user_id: str = Form(...)
):
    try:
        # Validate inputs
        if not user_id or user_id.strip() == "":
            raise HTTPException(status_code=400, detail="User ID is required")
        
        if not ObjectId.is_valid(user_challenge_id):
            raise HTTPException(status_code=400, detail="Invalid challenge ID format")
        
        # Get user challenge
        user_challenge = user_challenges_collection.find_one({
            "_id": ObjectId(user_challenge_id),
            "user_id": user_id
        })
        
        if not user_challenge:
            raise HTTPException(status_code=404, detail="Challenge not found or doesn't belong to you")
        
        if not user_challenge.get("completed", False):
            return {"success": False, "message": "Challenge not completed yet"}
        
        if user_challenge.get("reward_claimed", False):
            return {"success": False, "message": "Reward already claimed"}
        
        # Award points to user
        reward_points = user_challenge.get("reward_points", 0)
        
        # Debug: Log the user_id and reward_points
        print(f"DEBUG: Claiming reward for user_id={user_id}, reward_points={reward_points}")
        
        # Find the user first to check if ecoPoints field exists
        user = users_collection.find_one({"$or": [{"mobile": user_id}, {"email": user_id}]})
        
        if not user:
            print(f"DEBUG: User not found with identifier: {user_id}")
            raise HTTPException(status_code=404, detail=f"User not found with identifier: {user_id}")
        
        # Check if ecoPoints field exists, if not initialize it
        if "ecoPoints" not in user:
            print(f"DEBUG: Initializing ecoPoints field for user {user_id}")
            users_collection.update_one(
                {"_id": user["_id"]},
                {"$set": {"ecoPoints": 0}}
            )
        
        # Now increment the points
        user_update_result = users_collection.update_one(
            {"_id": user["_id"]},
            {"$inc": {"ecoPoints": reward_points}}
        )
        
        # Debug: Log the update result
        print(f"DEBUG: Update result - matched_count={user_update_result.matched_count}, modified_count={user_update_result.modified_count}")
        
        if user_update_result.matched_count == 0:
            print(f"DEBUG: Failed to update user points")
            raise HTTPException(status_code=500, detail="Failed to update user points")
        
        # Mark reward as claimed
        user_challenges_collection.update_one(
            {"_id": ObjectId(user_challenge_id)},
            {"$set": {
                "reward_claimed": True, 
                "status": "claimed",
                "claimed_at": datetime.now(pytz.UTC)
            }}
        )
        
        print(f"DEBUG: Successfully claimed reward - {reward_points} points added to user {user_id}")
        
        return {
            "success": True,
            "message": f"Reward claimed! +{reward_points} Eco Points",
            "points_awarded": reward_points
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"ERROR in claim_reward: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error claiming reward: {str(e)}")


# Get challenge details
@router.get("/challenges/{challenge_id}")
async def get_challenge_details(challenge_id: str):
    try:
        challenge = challenges_collection.find_one(
            {"challenge_id": challenge_id},
            {"_id": 0}
        )
        
        if not challenge:
            raise HTTPException(status_code=404, detail="Challenge not found")
        
        return {"success": True, "challenge": challenge}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Test endpoint to check if challenges exist
@router.get("/challenges/test")
async def test_challenges():
    try:
        challenges = list(challenges_collection.find(
            {"type": "daily_checkin", "active": True},
            {"_id": 0}
        ))
        return {
            "success": True, 
            "count": len(challenges),
            "challenges": challenges[:3]  # Return first 3 for testing
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


# ============================================================================
# ADMIN ENDPOINTS FOR CHALLENGE MANAGEMENT
# ============================================================================

# Helper function to get current admin (placeholder - implement proper auth)
def get_current_admin():
    # TODO: Implement proper admin authentication
    return {"admin_id": "admin", "role": "admin"}

# List all challenges with filtering and sorting
@router.get("/admin/challenges")
async def list_challenges(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    status: Optional[str] = Query(None),
    difficulty: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    sort_by: str = Query("created_at", pattern="^(created_at|title|participants|completion_rate)$"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$"),
    admin_data: dict = Depends(verify_admin_token)
):
    """List challenges with filtering and sorting for admin"""
    try:
        # Build filter query
        filter_query = {"type": "daily_checkin"}
        
        if status:
            if status == "active":
                filter_query["active"] = True
            elif status == "inactive":
                filter_query["active"] = False
        
        if difficulty:
            filter_query["difficulty"] = difficulty
            
        if category:
            filter_query["category"] = category
            
        if search:
            filter_query["$or"] = [
                {"title": {"$regex": search, "$options": "i"}},
                {"description": {"$regex": search, "$options": "i"}},
                {"challenge_id": {"$regex": search, "$options": "i"}}
            ]
        
        # Get total count
        total = challenges_collection.count_documents(filter_query)
        
        # Build sort query
        sort_direction = -1 if sort_order == "desc" else 1
        sort_field = sort_by
        
        # Get challenges
        challenges_cursor = challenges_collection.find(filter_query).sort(sort_field, sort_direction).skip(skip).limit(limit)
        challenges = list(challenges_cursor)
        
        # Add statistics for each challenge
        for challenge in challenges:
            challenge["_id"] = str(challenge["_id"])
            
            # Get participation stats
            stats = await get_challenge_statistics(challenge["challenge_id"])
            challenge["stats"] = stats
        
        return {
            "success": True,
            "total": total,
            "skip": skip,
            "limit": limit,
            "challenges": challenges
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching challenges: {str(e)}")

# Create new challenge
@router.post("/admin/challenges")
async def create_challenge(
    challenge: ChallengeCreate,
    admin_data: dict = Depends(verify_admin_token)
):
    """Create a new challenge"""
    try:
        # Check if challenge_id already exists
        existing = challenges_collection.find_one({"challenge_id": challenge.challenge_id})
        if existing:
            raise HTTPException(status_code=400, detail="Challenge ID already exists")
        
        # Create challenge document
        challenge_doc = {
            "challenge_id": challenge.challenge_id,
            "title": challenge.title,
            "description": challenge.description,
            "type": "daily_checkin",
            "duration_days": challenge.duration_days,
            "reward_points": challenge.reward_points,
            "category": challenge.category,
            "icon": challenge.icon,
            "difficulty": challenge.difficulty,
            "tips": challenge.tips,
            "active": True,  # New challenges are active by default
            "allow_one_skip": challenge.allow_one_skip,
            "featured": challenge.featured,
            "tags": challenge.tags,
            "admin_notes": challenge.admin_notes,
            "created_at": datetime.now(pytz.UTC),
            "created_by": "admin",  # TODO: Get from auth
            "updated_at": datetime.now(pytz.UTC),
            "updated_by": "admin"
        }
        
        result = challenges_collection.insert_one(challenge_doc)
        challenge_doc["_id"] = str(result.inserted_id)
        
        return {
            "success": True,
            "message": "Challenge created successfully",
            "challenge": challenge_doc
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating challenge: {str(e)}")

# Get challenge analytics (MUST be before {challenge_id} route)
@router.get("/admin/challenges/analytics")
async def get_challenge_analytics(admin_data: dict = Depends(verify_admin_token)):
    """Get overall challenge analytics for admin dashboard"""
    try:
        # Total challenges
        total_challenges = challenges_collection.count_documents({"type": "daily_checkin"})
        active_challenges = challenges_collection.count_documents({"type": "daily_checkin", "active": True})
        
        # Total participants across all challenges
        total_participants = user_challenges_collection.count_documents({})
        active_participants = user_challenges_collection.count_documents({"status": "in_progress"})
        completed_challenges = user_challenges_collection.count_documents({"status": {"$in": ["completed", "claimed"]}})
        
        # Overall completion rate
        overall_completion_rate = (completed_challenges / total_participants * 100) if total_participants > 0 else 0
        
        # Total points awarded
        total_points_pipeline = [
            {"$match": {"status": "claimed", "reward_claimed": True}},
            {"$group": {"_id": None, "total": {"$sum": "$reward_points"}}}
        ]
        points_result = list(user_challenges_collection.aggregate(total_points_pipeline))
        total_points_awarded = points_result[0]["total"] if points_result else 0
        
        # Challenge performance (top 5 by participation)
        challenge_performance_pipeline = [
            {"$group": {
                "_id": "$challenge_id",
                "participants": {"$sum": 1},
                "completed": {"$sum": {"$cond": [{"$in": ["$status", ["completed", "claimed"]]}, 1, 0]}},
                "avg_streak": {"$avg": "$current_streak"}
            }},
            {"$addFields": {
                "completion_rate": {"$multiply": [{"$divide": ["$completed", "$participants"]}, 100]}
            }},
            {"$sort": {"participants": -1}},
            {"$limit": 5}
        ]
        
        challenge_performance = list(user_challenges_collection.aggregate(challenge_performance_pipeline))
        
        # Add challenge titles
        for perf in challenge_performance:
            challenge = challenges_collection.find_one({"challenge_id": perf["_id"]}, {"title": 1, "icon": 1})
            if challenge:
                perf["title"] = challenge.get("title", perf["_id"])
                perf["icon"] = challenge.get("icon", "🎯")
            else:
                perf["title"] = perf["_id"]
                perf["icon"] = "🎯"
        
        # Daily activity (last 30 days)
        daily_activity = {}
        for i in range(30):
            date = (datetime.now(pytz.UTC) - timedelta(days=i)).strftime("%Y-%m-%d")
            checkins = user_challenges_collection.count_documents({
                "check_ins": {
                    "$elemMatch": {
                        "date": date,
                        "checked_in": True
                    }
                }
            })
            daily_activity[date] = checkins
        
        return {
            "success": True,
            "analytics": {
                "total_challenges": total_challenges,
                "active_challenges": active_challenges,
                "total_participants": total_participants,
                "active_participants": active_participants,
                "completed_challenges": completed_challenges,
                "overall_completion_rate": round(overall_completion_rate, 1),
                "total_points_awarded": total_points_awarded,
                "challenge_performance": challenge_performance,
                "daily_activity": daily_activity
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching analytics: {str(e)}")

# Get challenge details
@router.get("/admin/challenges/{challenge_id}")
async def get_admin_challenge_details(challenge_id: str):
    """Get detailed challenge information for admin"""
    try:
        challenge = challenges_collection.find_one({"challenge_id": challenge_id})
        
        if not challenge:
            raise HTTPException(status_code=404, detail="Challenge not found")
        
        challenge["_id"] = str(challenge["_id"])
        
        # Get detailed statistics
        stats = await get_challenge_statistics(challenge_id)
        challenge["stats"] = stats
        
        # Get recent participants
        recent_participants = list(user_challenges_collection.find(
            {"challenge_id": challenge_id},
            {"user_id": 1, "status": 1, "started_at": 1, "current_streak": 1}
        ).sort("started_at", -1).limit(10))
        
        for participant in recent_participants:
            participant["_id"] = str(participant["_id"])
            if participant.get("started_at"):
                participant["started_at"] = participant["started_at"].isoformat()
        
        challenge["recent_participants"] = recent_participants
        
        return {
            "success": True,
            "challenge": challenge
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching challenge details: {str(e)}")

# Update challenge
@router.put("/admin/challenges/{challenge_id}")
async def update_challenge(challenge_id: str, challenge_update: ChallengeUpdate):
    """Update an existing challenge"""
    try:
        # Check if challenge exists
        existing = challenges_collection.find_one({"challenge_id": challenge_id})
        if not existing:
            raise HTTPException(status_code=404, detail="Challenge not found")
        
        # Build update document
        update_doc = {}
        if challenge_update.title is not None:
            update_doc["title"] = challenge_update.title
        if challenge_update.description is not None:
            update_doc["description"] = challenge_update.description
        if challenge_update.duration_days is not None:
            update_doc["duration_days"] = challenge_update.duration_days
        if challenge_update.reward_points is not None:
            update_doc["reward_points"] = challenge_update.reward_points
        if challenge_update.difficulty is not None:
            update_doc["difficulty"] = challenge_update.difficulty
        if challenge_update.tips is not None:
            update_doc["tips"] = challenge_update.tips
        if challenge_update.active is not None:
            update_doc["active"] = challenge_update.active
        if challenge_update.featured is not None:
            update_doc["featured"] = challenge_update.featured
        if challenge_update.tags is not None:
            update_doc["tags"] = challenge_update.tags
        if challenge_update.admin_notes is not None:
            update_doc["admin_notes"] = challenge_update.admin_notes
        
        # Add update metadata
        update_doc["updated_at"] = datetime.now(pytz.UTC)
        update_doc["updated_by"] = "admin"  # TODO: Get from auth
        
        # Update challenge
        result = challenges_collection.update_one(
            {"challenge_id": challenge_id},
            {"$set": update_doc}
        )
        
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Challenge not found")
        
        # Get updated challenge
        updated_challenge = challenges_collection.find_one({"challenge_id": challenge_id})
        updated_challenge["_id"] = str(updated_challenge["_id"])
        
        return {
            "success": True,
            "message": "Challenge updated successfully",
            "challenge": updated_challenge
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating challenge: {str(e)}")

# Delete challenge (soft delete)
@router.delete("/admin/challenges/{challenge_id}")
async def delete_challenge(challenge_id: str):
    """Delete a challenge (soft delete by marking as inactive)"""
    try:
        # Check if challenge exists
        existing = challenges_collection.find_one({"challenge_id": challenge_id})
        if not existing:
            raise HTTPException(status_code=404, detail="Challenge not found")
        
        # Check if there are active user challenges
        active_user_challenges = user_challenges_collection.count_documents({
            "challenge_id": challenge_id,
            "status": "in_progress"
        })
        
        if active_user_challenges > 0:
            # Soft delete - mark as inactive
            challenges_collection.update_one(
                {"challenge_id": challenge_id},
                {"$set": {
                    "active": False,
                    "archived_at": datetime.now(pytz.UTC),
                    "archived_by": "admin"  # TODO: Get from auth
                }}
            )
            message = f"Challenge deactivated (had {active_user_challenges} active participants)"
        else:
            # Hard delete if no active participants
            challenges_collection.delete_one({"challenge_id": challenge_id})
            message = "Challenge deleted permanently"
        
        return {
            "success": True,
            "message": message
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting challenge: {str(e)}")

# Toggle challenge active status
@router.post("/admin/challenges/{challenge_id}/toggle")
async def toggle_challenge_status(challenge_id: str, active: bool = Query(...)):
    """Activate or deactivate a challenge"""
    try:
        result = challenges_collection.update_one(
            {"challenge_id": challenge_id},
            {"$set": {
                "active": active,
                "updated_at": datetime.now(pytz.UTC),
                "updated_by": "admin"  # TODO: Get from auth
            }}
        )
        
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Challenge not found")
        
        status_text = "activated" if active else "deactivated"
        return {
            "success": True,
            "message": f"Challenge {status_text} successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error toggling challenge status: {str(e)}")

# Get challenge statistics
async def get_challenge_statistics(challenge_id: str) -> Dict[str, Any]:
    """Get detailed statistics for a challenge"""
    try:
        # Get all user challenges for this challenge
        user_challenges = list(user_challenges_collection.find({"challenge_id": challenge_id}))
        
        total_participants = len(user_challenges)
        active_participants = len([uc for uc in user_challenges if uc.get("status") == "in_progress"])
        completed_participants = len([uc for uc in user_challenges if uc.get("status") in ["completed", "claimed"]])
        
        completion_rate = (completed_participants / total_participants * 100) if total_participants > 0 else 0
        
        # Calculate average streak
        streaks = [uc.get("current_streak", 0) for uc in user_challenges if uc.get("current_streak", 0) > 0]
        avg_streak = sum(streaks) / len(streaks) if streaks else 0
        
        # Calculate total points awarded
        total_points_awarded = sum([
            uc.get("reward_points", 0) for uc in user_challenges 
            if uc.get("status") == "claimed" and uc.get("reward_claimed", False)
        ])
        
        # Calculate average completion time (for completed challenges)
        completion_times = []
        for uc in user_challenges:
            if uc.get("status") in ["completed", "claimed"] and uc.get("started_at") and uc.get("completed_at"):
                start_time = uc["started_at"]
                end_time = uc.get("completed_at") or uc.get("claimed_at")
                if end_time:
                    duration = (end_time - start_time).days
                    completion_times.append(duration)
        
        avg_completion_time = sum(completion_times) / len(completion_times) if completion_times else 0
        
        # Daily participation (last 7 days)
        daily_participation = {}
        for i in range(7):
            date = (datetime.now(pytz.UTC) - timedelta(days=i)).strftime("%Y-%m-%d")
            count = user_challenges_collection.count_documents({
                "challenge_id": challenge_id,
                "check_ins": {
                    "$elemMatch": {
                        "date": date,
                        "checked_in": True
                    }
                }
            })
            daily_participation[date] = count
        
        return {
            "total_participants": total_participants,
            "active_participants": active_participants,
            "completed_participants": completed_participants,
            "completion_rate": round(completion_rate, 1),
            "avg_streak": round(avg_streak, 1),
            "total_points_awarded": total_points_awarded,
            "avg_completion_time": round(avg_completion_time, 1),
            "daily_participation": daily_participation
        }
        
    except Exception as e:
        print(f"Error calculating challenge statistics: {str(e)}")
        return {
            "total_participants": 0,
            "active_participants": 0,
            "completed_participants": 0,
            "completion_rate": 0,
            "avg_streak": 0,
            "total_points_awarded": 0,
            "avg_completion_time": 0,
            "daily_participation": {}
        }

# Get challenge participants
@router.get("/admin/challenges/{challenge_id}/participants")
async def get_challenge_participants(
    challenge_id: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    status: Optional[str] = Query(None)
):
    """Get participants for a specific challenge"""
    try:
        # Build filter
        filter_query = {"challenge_id": challenge_id}
        if status:
            filter_query["status"] = status
        
        # Get total count
        total = user_challenges_collection.count_documents(filter_query)
        
        # Get participants
        participants = list(user_challenges_collection.find(
            filter_query,
            {
                "user_id": 1,
                "status": 1,
                "started_at": 1,
                "completed_at": 1,
                "current_streak": 1,
                "missed_days": 1,
                "reward_claimed": 1
            }
        ).sort("started_at", -1).skip(skip).limit(limit))
        
        # Format response
        for participant in participants:
            participant["_id"] = str(participant["_id"])
            if participant.get("started_at"):
                participant["started_at"] = participant["started_at"].isoformat()
            if participant.get("completed_at"):
                participant["completed_at"] = participant["completed_at"].isoformat()
        
        return {
            "success": True,
            "total": total,
            "skip": skip,
            "limit": limit,
            "participants": participants
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching participants: {str(e)}")
