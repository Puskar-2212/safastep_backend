from fastapi import APIRouter, HTTPException, Form
from database import user_db
from datetime import datetime, timedelta
from typing import Optional
import pytz
from bson import ObjectId

router = APIRouter()

# Get collections
challenges_collection = user_db["challenges"]
user_challenges_collection = user_db["user_challenges"]
users_collection = user_db["user_data"]

# Get all available daily check-in challenges
@router.get("/challenges/daily-checkin")
async def get_daily_checkin_challenges():
    try:
        challenges = list(challenges_collection.find(
            {"type": "daily_checkin", "active": True},
            {"_id": 0}
        ))
        return {"success": True, "challenges": challenges}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Accept/Start a challenge
@router.post("/challenges/{challenge_id}/accept")
async def accept_challenge(
    challenge_id: str,
    user_id: str = Form(...)
):
    try:
        # Validate user_id
        if not user_id or user_id.strip() == "":
            raise HTTPException(status_code=400, detail="User ID is required")
        
        # Check if challenge exists
        challenge = challenges_collection.find_one({"challenge_id": challenge_id, "active": True})
        if not challenge:
            raise HTTPException(status_code=404, detail="Challenge not found or inactive")
        
        # Check if user already has this challenge active
        existing = user_challenges_collection.find_one({
            "user_id": user_id,
            "challenge_id": challenge_id,
            "status": {"$in": ["in_progress", "completed"]}
        })
        
        if existing:
            return {"success": False, "message": "You already have this challenge active or completed"}
        
        # Create check-ins array for all days
        check_ins = []
        start_date = datetime.now(pytz.UTC)
        
        for day in range(1, challenge["duration_days"] + 1):
            check_ins.append({
                "day": day,
                "date": (start_date + timedelta(days=day-1)).strftime("%Y-%m-%d"),
                "checked_in": False,
                "timestamp": None,
                "note": None
            })
        
        # Create user challenge
        user_challenge = {
            "user_id": user_id,
            "challenge_id": challenge_id,
            "challenge_title": challenge["title"],
            "challenge_icon": challenge.get("icon", "🎯"),
            "challenge_category": challenge.get("category", "general"),
            "status": "in_progress",
            "started_at": start_date,
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
        
        result = user_challenges_collection.insert_one(user_challenge)
        user_challenge["_id"] = str(result.inserted_id)
        
        return {
            "success": True,
            "message": "Challenge accepted!",
            "user_challenge": user_challenge
        }
        
    except HTTPException:
        raise
    except Exception as e:
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
        today = datetime.now(pytz.UTC).strftime("%Y-%m-%d")
        
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
        
        # Check if user missed previous days
        missed_days = 0
        for i, checkin in enumerate(check_ins):
            if i < today_index:  # Only check past days
                past_date = datetime.strptime(checkin["date"], "%Y-%m-%d").date()
                if past_date < datetime.now(pytz.UTC).date() and not checkin["checked_in"]:
                    missed_days += 1
        
        # Update check-in
        check_ins[today_index]["checked_in"] = True
        check_ins[today_index]["timestamp"] = datetime.now(pytz.UTC)
        check_ins[today_index]["note"] = note if note and note.strip() else None
        
        # Calculate current streak (consecutive days from start)
        current_streak = 0
        for checkin in check_ins:
            if checkin["checked_in"]:
                current_streak += 1
            else:
                # Stop counting if we hit an unchecked day
                break
        
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
        
        challenges = list(user_challenges_collection.find(
            {"user_id": user_id, "status": {"$in": ["in_progress", "completed", "claimed"]}}
        ).sort("started_at", -1))  # Sort by most recent first
        
        # Convert ObjectId to string and handle datetime serialization
        for challenge in challenges:
            challenge["_id"] = str(challenge["_id"])
            if "started_at" in challenge and challenge["started_at"]:
                challenge["started_at"] = challenge["started_at"].isoformat()
            if "completed_at" in challenge and challenge["completed_at"]:
                challenge["completed_at"] = challenge["completed_at"].isoformat()
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

