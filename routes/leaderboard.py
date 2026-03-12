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
    
    Note: For 'all' period, uses ecoPoints from users collection (accurate total).
          For 'week' and 'month', calculates from posts in that period.
    """
    try:
        if period == "all":
            # For all-time leaderboard, use ecoPoints from users collection
            users = list(users_collection.find({}, {
                "mobile": 1,
                "email": 1,
                "firstName": 1,
                "lastName": 1,
                "profilePicture": 1,
                "ecoPoints": 1,
                "totalCO2Offset": 1
            }).sort("ecoPoints", -1).limit(limit))
            
            enriched_leaderboard = []
            for idx, user in enumerate(users):
                identifier = user.get("mobile") or user.get("email")
                eco_points = user.get("ecoPoints", 0)
                
                # Count user's posts
                post_count = posts_collection.count_documents({"identifier": identifier})
                
                enriched_leaderboard.append({
                    "rank": idx + 1,
                    "identifier": identifier,
                    "name": f"{user.get('firstName', '')} {user.get('lastName', '')}".strip(),
                    "firstName": user.get("firstName", "Anonymous"),
                    "lastName": user.get("lastName", "User"),
                    "profilePicture": user.get("profilePicture"),
                    "ecoPoints": eco_points,
                    "co2Reduced": round(user.get("totalCO2Offset", 0), 2),
                    "carbonCredits": eco_points,
                    "postCount": post_count,
                    "isActive": post_count > 0
                })
            
            return {
                "success": True,
                "period": period,
                "totalUsers": len(enriched_leaderboard),
                "leaderboard": enriched_leaderboard
            }
        
        # For week/month periods, calculate from posts in that time range
        date_filter = {}
        if period == "week":
            week_ago = datetime.now() - timedelta(days=7)
            date_filter = {"createdAt": {"$gte": int(week_ago.timestamp())}}
        elif period == "month":
            month_ago = datetime.now() - timedelta(days=30)
            date_filter = {"createdAt": {"$gte": int(month_ago.timestamp())}}
        
        # Aggregate eco points per user from posts
        pipeline = [
            {"$match": date_filter},
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
        # Get user info
        user = users_collection.find_one({
            "$or": [
                {"mobile": identifier},
                {"email": identifier}
            ]
        })
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        if period == "all":
            # For all-time, use ecoPoints from user document
            eco_points = user.get("ecoPoints", 0)
            co2_offset = user.get("totalCO2Offset", 0)
            post_count = posts_collection.count_documents({"identifier": identifier})
            
            # Count users with more points
            users_ahead = users_collection.count_documents({"ecoPoints": {"$gt": eco_points}})
            rank = users_ahead + 1
            
            return {
                "success": True,
                "rank": rank,
                "identifier": identifier,
                "name": f"{user.get('firstName', '')} {user.get('lastName', '')}".strip(),
                "ecoPoints": eco_points,
                "co2Reduced": round(co2_offset, 2),
                "carbonCredits": eco_points,
                "postCount": post_count,
                "period": period
            }
        
        # For week/month, calculate from posts in that period
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
        
        # If user has no posts in this period, they have 0 points
        if not user_data:
            # Count total users with posts in this period
            base_filter = {}
            if period == "week":
                week_ago = datetime.now() - timedelta(days=7)
                base_filter = {"createdAt": {"$gte": int(week_ago.timestamp())}}
            elif period == "month":
                month_ago = datetime.now() - timedelta(days=30)
                base_filter = {"createdAt": {"$gte": int(month_ago.timestamp())}}
            
            users_with_points_pipeline = [
                {"$match": base_filter},
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
            {"$match": base_filter},
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
