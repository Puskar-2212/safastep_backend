from fastapi import APIRouter, HTTPException, Query
from database import users_collection, posts_collection
from typing import Optional
from datetime import datetime, timedelta

router = APIRouter()

@router.get("/leaderboard")
async def get_leaderboard(
    period: Optional[str] = Query("all", regex="^(week|month|all)$"),
    limit: Optional[int] = Query(50, ge=1, le=100)
):
    """
    Get leaderboard data based on eco points earned
    
    Parameters:
    - period: Filter by time period (week, month, all)
    - limit: Maximum number of users to return (default 50, max 100)
    """
    try:
        # Calculate date filter based on period
        date_filter = {}
        if period == "week":
            week_ago = datetime.now() - timedelta(days=7)
            date_filter = {"createdAt": {"$gte": int(week_ago.timestamp())}}
        elif period == "month":
            month_ago = datetime.now() - timedelta(days=30)
            date_filter = {"createdAt": {"$gte": int(month_ago.timestamp())}}
        
        # Aggregate eco points per user from posts
        pipeline = [
            {"$match": date_filter} if date_filter else {"$match": {}},
            {
                "$group": {
                    "_id": "$identifier",
                    "totalEcoPoints": {"$sum": "$ecoPoints"},
                    "totalCO2Reduced": {"$sum": "$co2Offset"},
                    "postCount": {"$sum": 1}
                }
            },
            {"$sort": {"totalEcoPoints": -1}},
            {"$limit": limit}
        ]
        
        # Get aggregated data from posts collection
        leaderboard_data = list(posts_collection.aggregate(pipeline))
        
        # Get all users who have posts
        users_with_posts = {entry["_id"] for entry in leaderboard_data}
        
        # Get all users from database
        all_users = list(users_collection.find({}, {
            "mobile": 1,
            "email": 1,
            "firstName": 1,
            "lastName": 1,
            "profilePicture": 1
        }))
        
        # Create a map of user data
        user_map = {}
        for user in all_users:
            identifier = user.get("mobile") or user.get("email")
            if identifier:
                user_map[identifier] = user
        
        # Enrich with user data
        enriched_leaderboard = []
        for idx, entry in enumerate(leaderboard_data):
            identifier = entry["_id"]
            user = user_map.get(identifier)
            
            if user:
                enriched_leaderboard.append({
                    "rank": idx + 1,
                    "identifier": identifier,
                    "name": f"{user.get('firstName', '')} {user.get('lastName', '')}".strip(),
                    "firstName": user.get("firstName", "Anonymous"),
                    "lastName": user.get("lastName", "User"),
                    "profilePicture": user.get("profilePicture"),
                    "ecoPoints": entry["totalEcoPoints"],
                    "co2Reduced": round(entry["totalCO2Reduced"], 2),
                    "carbonCredits": entry["totalEcoPoints"],
                    "postCount": entry["postCount"],
                    "isActive": entry["postCount"] > 0
                })
        
        # Add users with 0 points (no posts)
        current_rank = len(enriched_leaderboard) + 1
        for identifier, user in user_map.items():
            if identifier not in users_with_posts:
                enriched_leaderboard.append({
                    "rank": current_rank,
                    "identifier": identifier,
                    "name": f"{user.get('firstName', '')} {user.get('lastName', '')}".strip(),
                    "firstName": user.get("firstName", "Anonymous"),
                    "lastName": user.get("lastName", "User"),
                    "profilePicture": user.get("profilePicture"),
                    "ecoPoints": 0,
                    "co2Reduced": 0,
                    "carbonCredits": 0,
                    "postCount": 0,
                    "isActive": False
                })
                current_rank += 1
                
                # Stop if we've reached the limit
                if len(enriched_leaderboard) >= limit:
                    break
        
        return {
            "success": True,
            "period": period,
            "totalUsers": len(enriched_leaderboard),
            "leaderboard": enriched_leaderboard
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching leaderboard: {str(e)}")


@router.get("/leaderboard/user/{identifier}")
async def get_user_rank(identifier: str, period: Optional[str] = Query("all", regex="^(week|month|all)$")):
    """
    Get a specific user's rank and stats in the leaderboard
    
    Parameters:
    - identifier: User's mobile or email
    - period: Filter by time period (week, month, all)
    """
    try:
        # Calculate date filter based on period
        date_filter = {"identifier": identifier}
        if period == "week":
            week_ago = datetime.now() - timedelta(days=7)
            date_filter["createdAt"] = {"$gte": int(week_ago.timestamp())}
        elif period == "month":
            month_ago = datetime.now() - timedelta(days=30)
            date_filter["createdAt"] = {"$gte": int(month_ago.timestamp())}
        
        # Get user's total eco points from posts
        user_pipeline = [
            {"$match": date_filter},
            {
                "$group": {
                    "_id": "$identifier",
                    "totalEcoPoints": {"$sum": "$ecoPoints"},
                    "totalCO2Reduced": {"$sum": "$co2Offset"},
                    "postCount": {"$sum": 1}
                }
            }
        ]
        
        user_data = list(posts_collection.aggregate(user_pipeline))
        
        # Get user info
        user = users_collection.find_one({
            "$or": [
                {"mobile": identifier},
                {"email": identifier}
            ]
        })
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # If user has no posts, they have 0 points
        if not user_data:
            # Count total users with posts
            base_filter = {}
            if period == "week":
                week_ago = datetime.now() - timedelta(days=7)
                base_filter = {"createdAt": {"$gte": int(week_ago.timestamp())}}
            elif period == "month":
                month_ago = datetime.now() - timedelta(days=30)
                base_filter = {"createdAt": {"$gte": int(month_ago.timestamp())}}
            
            users_with_points_pipeline = [
                {"$match": base_filter} if base_filter else {"$match": {}},
                {
                    "$group": {
                        "_id": "$identifier",
                        "totalEcoPoints": {"$sum": "$ecoPoints"}
                    }
                },
                {"$count": "total"}
            ]
            
            users_with_points = list(posts_collection.aggregate(users_with_points_pipeline))
            rank = users_with_points[0]["total"] + 1 if users_with_points else 1
            
            return {
                "success": True,
                "rank": rank,
                "identifier": identifier,
                "name": f"{user.get('firstName', '')} {user.get('lastName', '')}".strip(),
                "ecoPoints": 0,
                "co2Reduced": 0,
                "carbonCredits": 0,
                "postCount": 0,
                "period": period
            }
        
        user_points = user_data[0]["totalEcoPoints"]
        
        # Count how many users have more points (to determine rank)
        base_filter = {}
        if period == "week":
            week_ago = datetime.now() - timedelta(days=7)
            base_filter = {"createdAt": {"$gte": int(week_ago.timestamp())}}
        elif period == "month":
            month_ago = datetime.now() - timedelta(days=30)
            base_filter = {"createdAt": {"$gte": int(month_ago.timestamp())}}
        
        rank_pipeline = [
            {"$match": base_filter} if base_filter else {"$match": {}},
            {
                "$group": {
                    "_id": "$identifier",
                    "totalEcoPoints": {"$sum": "$ecoPoints"}
                }
            },
            {
                "$match": {
                    "totalEcoPoints": {"$gt": user_points}
                }
            },
            {"$count": "usersAhead"}
        ]
        
        rank_result = list(posts_collection.aggregate(rank_pipeline))
        rank = rank_result[0]["usersAhead"] + 1 if rank_result else 1
        
        return {
            "success": True,
            "rank": rank,
            "identifier": identifier,
            "name": f"{user.get('firstName', '')} {user.get('lastName', '')}".strip(),
            "ecoPoints": user_data[0]["totalEcoPoints"],
            "co2Reduced": round(user_data[0]["totalCO2Reduced"], 2),
            "carbonCredits": user_data[0]["totalEcoPoints"],
            "postCount": user_data[0]["postCount"],
            "period": period
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching user rank: {str(e)}")
