from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from database import users_collection, posts_collection, likes_collection, eco_locations_collection
import logging
from bson import ObjectId

logger = logging.getLogger(__name__)
router = APIRouter()

# Pydantic models
class EcoLocation(BaseModel):
    name: str
    description: str
    latitude: float
    longitude: float
    category: str
    address: str

class EcoLocationUpdate(BaseModel):
    name: str = None
    description: str = None
    latitude: float = None
    longitude: float = None
    category: str = None
    address: str = None

# Admin authentication middleware would go here
# For now, using simple token validation

@router.get("/admin/users")
async def get_all_users(skip: int = Query(0, ge=0), limit: int = Query(10, ge=1, le=100)):
    """Get all users with pagination"""
    try:
        total = users_collection.count_documents({})
        users = list(users_collection.find({}).skip(skip).limit(limit))
        
        # Convert ObjectId to string
        for user in users:
            user["_id"] = str(user["_id"])
        
        return {
            "success": True,
            "total": total,
            "skip": skip,
            "limit": limit,
            "users": users
        }
    except Exception as e:
        logger.error(f"Error fetching users: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch users")

@router.get("/admin/users/search")
async def search_users(query: str = Query(..., min_length=1), skip: int = Query(0, ge=0), limit: int = Query(10, ge=1, le=100)):
    """Search users by name, email, or mobile - supports partial keyword matching"""
    try:
        import re
        
        # Clean and escape the query
        query = query.strip()
        
        # Split query into keywords for multi-word search
        keywords = query.split()
        
        search_conditions = []
        
        # For each keyword, search in firstName, lastName, email, mobile
        for keyword in keywords:
            escaped_keyword = re.escape(keyword)
            search_conditions.extend([
                {"firstName": {"$regex": escaped_keyword, "$options": "i"}},
                {"lastName": {"$regex": escaped_keyword, "$options": "i"}},
                {"email": {"$regex": escaped_keyword, "$options": "i"}},
                {"mobile": {"$regex": escaped_keyword, "$options": "i"}}
            ])
        
        # Also search for the full query as-is (for phrases)
        escaped_full_query = re.escape(query)
        search_conditions.extend([
            {"firstName": {"$regex": escaped_full_query, "$options": "i"}},
            {"lastName": {"$regex": escaped_full_query, "$options": "i"}},
            {"email": {"$regex": escaped_full_query, "$options": "i"}},
            {"mobile": {"$regex": escaped_full_query, "$options": "i"}}
        ])
        
        search_filter = {"$or": search_conditions}
        
        total = users_collection.count_documents(search_filter)
        users = list(users_collection.find(search_filter).skip(skip).limit(limit))
        
        for user in users:
            user["_id"] = str(user["_id"])
        
        return {
            "success": True,
            "total": total,
            "skip": skip,
            "limit": limit,
            "users": users
        }
    except Exception as e:
        logger.error(f"Error searching users: {e}")
        raise HTTPException(status_code=500, detail="Failed to search users")

@router.get("/admin/users/{user_id}")
async def get_user_details(user_id: str):
    """Get detailed information about a specific user"""
    try:
        from bson import ObjectId
        user = users_collection.find_one({"_id": ObjectId(user_id)})
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        user["_id"] = str(user["_id"])
        
        # Get user's posts count
        posts_count = posts_collection.count_documents({"mobile": user.get("mobile")})
        
        # Get user's likes count
        likes_count = likes_collection.count_documents({"mobile": user.get("mobile")})
        
        return {
            "success": True,
            "user": user,
            "stats": {
                "posts_count": posts_count,
                "likes_count": likes_count
            }
        }
    except Exception as e:
        logger.error(f"Error fetching user details: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch user details")

@router.delete("/admin/users/{user_id}")
async def delete_user(user_id: str):
    """Delete a user and all their associated data"""
    try:
        from bson import ObjectId
        user = users_collection.find_one({"_id": ObjectId(user_id)})
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        mobile = user.get("mobile")
        email = user.get("email")
        
        # Delete user's posts
        posts_deleted = posts_collection.delete_many({"mobile": mobile})
        
        # Delete user's likes
        likes_deleted = likes_collection.delete_many({"mobile": mobile})
        
        # Delete user
        users_collection.delete_one({"_id": ObjectId(user_id)})
        
        logger.info(f"User {user_id} deleted. Posts: {posts_deleted.deleted_count}, Likes: {likes_deleted.deleted_count}")
        
        return {
            "success": True,
            "message": "User deleted successfully",
            "deleted": {
                "user": 1,
                "posts": posts_deleted.deleted_count,
                "likes": likes_deleted.deleted_count
            }
        }
    except Exception as e:
        logger.error(f"Error deleting user: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete user")

@router.get("/admin/posts")
async def get_all_posts(skip: int = Query(0, ge=0), limit: int = Query(10, ge=1, le=100)):
    """Get all posts with pagination"""
    try:
        total = posts_collection.count_documents({})
        posts = list(posts_collection.find({}).sort("_id", -1).skip(skip).limit(limit))
        
        # Convert ObjectId to string and format data
        for post in posts:
            post["_id"] = str(post["_id"])
            if "createdAt" in post:
                post["createdAt"] = int(post["createdAt"])
            
            # Extract firstName and lastName from userName if not present
            if "userName" in post and "firstName" not in post:
                name_parts = post["userName"].split(" ", 1)
                post["firstName"] = name_parts[0]
                post["lastName"] = name_parts[1] if len(name_parts) > 1 else ""
        
        return {
            "success": True,
            "total": total,
            "skip": skip,
            "limit": limit,
            "posts": posts
        }
    except Exception as e:
        logger.error(f"Error fetching posts: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch posts")

@router.get("/admin/posts/search")
async def search_posts(query: str = Query(..., min_length=1), skip: int = Query(0, ge=0), limit: int = Query(10, ge=1, le=100)):
    """Search posts by caption or user name"""
    try:
        # Escape special regex characters
        import re
        escaped_query = re.escape(query)
        
        search_filter = {
            "$or": [
                {"caption": {"$regex": escaped_query, "$options": "i"}},
                {"firstName": {"$regex": escaped_query, "$options": "i"}},
                {"lastName": {"$regex": escaped_query, "$options": "i"}},
                {"mobile": {"$regex": escaped_query, "$options": "i"}},
                {"userName": {"$regex": escaped_query, "$options": "i"}}
            ]
        }
        
        total = posts_collection.count_documents(search_filter)
        posts = list(posts_collection.find(search_filter).sort("_id", -1).skip(skip).limit(limit))
        
        for post in posts:
            post["_id"] = str(post["_id"])
            if "createdAt" in post:
                post["createdAt"] = int(post["createdAt"])
            
            # Extract firstName and lastName from userName if not present
            if "userName" in post and "firstName" not in post:
                name_parts = post["userName"].split(" ", 1)
                post["firstName"] = name_parts[0]
                post["lastName"] = name_parts[1] if len(name_parts) > 1 else ""
        
        return {
            "success": True,
            "total": total,
            "skip": skip,
            "limit": limit,
            "posts": posts
        }
    except Exception as e:
        logger.error(f"Error searching posts: {e}")
        raise HTTPException(status_code=500, detail="Failed to search posts")

# Post Review Endpoints - MUST come before {post_id} route!

@router.get("/admin/posts/pending")
async def get_pending_posts(skip: int = Query(0, ge=0), limit: int = Query(10, ge=1, le=100)):
    """Get all posts pending admin review"""
    try:
        # Find posts with pending_review status
        total = posts_collection.count_documents({"verificationStatus": "pending_review"})
        posts = list(posts_collection.find(
            {"verificationStatus": "pending_review"}
        ).sort("createdAt", -1).skip(skip).limit(limit))
        
        # Convert ObjectId to string and enrich with user data
        for post in posts:
            post["_id"] = str(post["_id"])
            
            # Get user's profile picture for comparison
            identifier = post.get("identifier") or post.get("mobile") or post.get("email")
            if identifier:
                if '@' in identifier:
                    user = users_collection.find_one({"email": identifier})
                else:
                    user = users_collection.find_one({"mobile": identifier})
                
                if user:
                    post["userProfilePicture"] = user.get("profilePicture")
                    post["firstName"] = user.get("firstName")
                    post["lastName"] = user.get("lastName")
        
        return {
            "success": True,
            "total": total,
            "skip": skip,
            "limit": limit,
            "posts": posts
        }
    except Exception as e:
        logger.error(f"Error fetching pending posts: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch pending posts")

@router.get("/admin/posts/{post_id}")
async def get_post_details(post_id: str):
    """Get detailed information about a specific post"""
    try:
        from bson import ObjectId
        post = posts_collection.find_one({"_id": ObjectId(post_id)})
        
        if not post:
            raise HTTPException(status_code=404, detail="Post not found")
        
        post["_id"] = str(post["_id"])
        if "createdAt" in post:
            post["createdAt"] = int(post["createdAt"])
        
        # Get likes count for this post
        likes_count = likes_collection.count_documents({"postId": post_id})
        
        # Extract firstName and lastName from userName if not present
        if "userName" in post and "firstName" not in post:
            name_parts = post["userName"].split(" ", 1)
            post["firstName"] = name_parts[0]
            post["lastName"] = name_parts[1] if len(name_parts) > 1 else ""
        
        return {
            "success": True,
            "post": post,
            "stats": {
                "likes_count": likes_count
            }
        }
    except Exception as e:
        logger.error(f"Error fetching post details: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch post details")

@router.delete("/admin/posts/{post_id}")
async def delete_post(post_id: str):
    """Delete a post and all associated likes"""
    try:
        from bson import ObjectId
        post = posts_collection.find_one({"_id": ObjectId(post_id)})
        
        if not post:
            raise HTTPException(status_code=404, detail="Post not found")
        
        # Delete post's likes
        likes_deleted = likes_collection.delete_many({"postId": post_id})
        
        # Delete post
        posts_collection.delete_one({"_id": ObjectId(post_id)})
        
        logger.info(f"Post {post_id} deleted. Likes: {likes_deleted.deleted_count}")
        
        return {
            "success": True,
            "message": "Post deleted successfully",
            "deleted": {
                "post": 1,
                "likes": likes_deleted.deleted_count
            }
        }
    except Exception as e:
        logger.error(f"Error deleting post: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete post")

# Eco-Locations endpoints
@router.get("/admin/eco-locations")
async def get_all_eco_locations(skip: int = Query(0, ge=0), limit: int = Query(10, ge=1, le=100)):
    """Get all eco-locations with pagination"""
    try:
        total = eco_locations_collection.count_documents({})
        locations = list(eco_locations_collection.find({}).skip(skip).limit(limit))
        
        for location in locations:
            location["_id"] = str(location["_id"])
        
        return {
            "success": True,
            "total": total,
            "skip": skip,
            "limit": limit,
            "locations": locations
        }
    except Exception as e:
        logger.error(f"Error fetching eco-locations: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch eco-locations")

@router.get("/admin/eco-locations/search")
async def search_eco_locations(query: str = Query(..., min_length=1), skip: int = Query(0, ge=0), limit: int = Query(10, ge=1, le=100)):
    """Search eco-locations by name, category, or address"""
    try:
        # Escape special regex characters
        import re
        escaped_query = re.escape(query)
        
        search_filter = {
            "$or": [
                {"name": {"$regex": escaped_query, "$options": "i"}},
                {"category": {"$regex": escaped_query, "$options": "i"}},
                {"address": {"$regex": escaped_query, "$options": "i"}},
                {"description": {"$regex": escaped_query, "$options": "i"}}
            ]
        }
        
        total = eco_locations_collection.count_documents(search_filter)
        locations = list(eco_locations_collection.find(search_filter).skip(skip).limit(limit))
        
        for location in locations:
            location["_id"] = str(location["_id"])
        
        return {
            "success": True,
            "total": total,
            "skip": skip,
            "limit": limit,
            "locations": locations
        }
    except Exception as e:
        logger.error(f"Error searching eco-locations: {e}")
        raise HTTPException(status_code=500, detail="Failed to search eco-locations")

@router.post("/admin/eco-locations")
async def create_eco_location(location: EcoLocation):
    """Create a new eco-location"""
    try:
        location_data = location.dict()
        result = eco_locations_collection.insert_one(location_data)
        
        return {
            "success": True,
            "message": "Eco-location created successfully",
            "location_id": str(result.inserted_id)
        }
    except Exception as e:
        logger.error(f"Error creating eco-location: {e}")
        raise HTTPException(status_code=500, detail="Failed to create eco-location")

@router.get("/admin/eco-locations/{location_id}")
async def get_eco_location_details(location_id: str):
    """Get detailed information about a specific eco-location"""
    try:
        location = eco_locations_collection.find_one({"_id": ObjectId(location_id)})
        
        if not location:
            raise HTTPException(status_code=404, detail="Eco-location not found")
        
        location["_id"] = str(location["_id"])
        
        return {
            "success": True,
            "location": location
        }
    except Exception as e:
        logger.error(f"Error fetching eco-location details: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch eco-location details")

@router.put("/admin/eco-locations/{location_id}")
async def update_eco_location(location_id: str, location: EcoLocationUpdate):
    """Update an eco-location"""
    try:
        update_data = {k: v for k, v in location.dict().items() if v is not None}
        
        if not update_data:
            raise HTTPException(status_code=400, detail="No fields to update")
        
        result = eco_locations_collection.update_one(
            {"_id": ObjectId(location_id)},
            {"$set": update_data}
        )
        
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Eco-location not found")
        
        return {
            "success": True,
            "message": "Eco-location updated successfully"
        }
    except Exception as e:
        logger.error(f"Error updating eco-location: {e}")
        raise HTTPException(status_code=500, detail="Failed to update eco-location")

@router.delete("/admin/eco-locations/{location_id}")
async def delete_eco_location(location_id: str):
    """Delete an eco-location"""
    try:
        result = eco_locations_collection.delete_one({"_id": ObjectId(location_id)})
        
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Eco-location not found")
        
        logger.info(f"Eco-location {location_id} deleted")
        
        return {
            "success": True,
            "message": "Eco-location deleted successfully"
        }
    except Exception as e:
        logger.error(f"Error deleting eco-location: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete eco-location")


@router.get("/admin/posts/{post_id}/review-details")
async def get_post_review_details(post_id: str):
    """Get detailed information for post review including user profile"""
    try:
        post = posts_collection.find_one({"_id": ObjectId(post_id)})
        
        if not post:
            raise HTTPException(status_code=404, detail="Post not found")
        
        post["_id"] = str(post["_id"])
        
        # Get user details
        identifier = post.get("identifier") or post.get("mobile") or post.get("email")
        user = None
        if identifier:
            if '@' in identifier:
                user = users_collection.find_one({"email": identifier})
            else:
                user = users_collection.find_one({"mobile": identifier})
        
        return {
            "success": True,
            "post": post,
            "user": {
                "firstName": user.get("firstName") if user else "Unknown",
                "lastName": user.get("lastName") if user else "",
                "mobile": user.get("mobile") if user else None,
                "email": user.get("email") if user else None,
                "profilePicture": user.get("profilePicture") if user else None,
                "ecoPoints": user.get("ecoPoints", 0) if user else 0,
                "totalCO2Offset": user.get("totalCO2Offset", 0) if user else 0
            } if user else None
        }
    except Exception as e:
        logger.error(f"Error fetching post review details: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch post details")


class ApprovePostRequest(BaseModel):
    adminId: str
    notes: str = ""

@router.post("/admin/posts/{post_id}/approve")
async def approve_post(post_id: str, request: ApprovePostRequest):
    """Approve a pending post and award eco points"""
    try:
        import time
        from routes.posts import calculate_eco_impact
        
        post = posts_collection.find_one({"_id": ObjectId(post_id)})
        
        if not post:
            raise HTTPException(status_code=404, detail="Post not found")
        
        if post.get("verificationStatus") != "pending_review":
            raise HTTPException(status_code=400, detail="Post is not pending review")
        
        # Calculate eco points
        category = post.get("category", "")
        eco_points, co2_offset = calculate_eco_impact(category, 100)
        
        # Update post status
        posts_collection.update_one(
            {"_id": ObjectId(post_id)},
            {
                "$set": {
                    "verificationStatus": "approved",
                    "verificationScore": 100,
                    "ecoPoints": eco_points,
                    "co2Offset": co2_offset,
                    "adminReview": {
                        "reviewedBy": request.adminId,
                        "reviewedAt": time.time(),
                        "decision": "approved",
                        "notes": request.notes
                    },
                    "updatedAt": time.time()
                }
            }
        )
        
        # Award eco points to user
        identifier = post.get("identifier") or post.get("mobile") or post.get("email")
        if identifier:
            if '@' in identifier:
                users_collection.update_one(
                    {"email": identifier},
                    {
                        "$inc": {
                            "ecoPoints": eco_points,
                            "totalCO2Offset": co2_offset
                        }
                    }
                )
            else:
                users_collection.update_one(
                    {"mobile": identifier},
                    {
                        "$inc": {
                            "ecoPoints": eco_points,
                            "totalCO2Offset": co2_offset
                        }
                    }
                )
        
        logger.info(f"Post {post_id} approved by admin {request.adminId}. Awarded {eco_points} points")
        
        return {
            "success": True,
            "message": "Post approved successfully",
            "ecoPoints": eco_points,
            "co2Offset": co2_offset
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error approving post: {e}")
        raise HTTPException(status_code=500, detail="Failed to approve post")


class RejectPostRequest(BaseModel):
    adminId: str
    reason: str
    notes: str = ""

@router.post("/admin/posts/{post_id}/reject")
async def reject_post(post_id: str, request: RejectPostRequest):
    """Reject a pending post"""
    try:
        import time
        import os
        from config import UPLOAD_DIR
        
        post = posts_collection.find_one({"_id": ObjectId(post_id)})
        
        if not post:
            raise HTTPException(status_code=404, detail="Post not found")
        
        if post.get("verificationStatus") != "pending_review":
            raise HTTPException(status_code=400, detail="Post is not pending review")
        
        # Update post status
        posts_collection.update_one(
            {"_id": ObjectId(post_id)},
            {
                "$set": {
                    "verificationStatus": "rejected",
                    "adminReview": {
                        "reviewedBy": request.adminId,
                        "reviewedAt": time.time(),
                        "decision": "rejected",
                        "reason": request.reason,
                        "notes": request.notes
                    },
                    "updatedAt": time.time()
                }
            }
        )
        
        # Optionally delete the image file
        if "imageFilename" in post:
            file_path = os.path.join(UPLOAD_DIR, post["imageFilename"])
            if os.path.exists(file_path):
                os.remove(file_path)
                logger.info(f"Deleted image file: {post['imageFilename']}")
        
        logger.info(f"Post {post_id} rejected by admin {request.adminId}. Reason: {request.reason}")
        
        return {
            "success": True,
            "message": "Post rejected successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error rejecting post: {e}")
        raise HTTPException(status_code=500, detail="Failed to reject post")


@router.get("/admin/stats")
async def get_admin_stats():
    """Get admin dashboard statistics"""
    try:
        total_users = users_collection.count_documents({})
        total_posts = posts_collection.count_documents({})
        pending_posts = posts_collection.count_documents({"verificationStatus": "pending_review"})
        approved_posts = posts_collection.count_documents({"verificationStatus": "approved"})
        rejected_posts = posts_collection.count_documents({"verificationStatus": "rejected"})
        
        # Calculate total CO2 offset
        pipeline = [
            {"$match": {"verificationStatus": "approved"}},
            {"$group": {
                "_id": None,
                "totalCO2": {"$sum": "$co2Offset"},
                "totalPoints": {"$sum": "$ecoPoints"}
            }}
        ]
        result = list(posts_collection.aggregate(pipeline))
        total_co2 = result[0]["totalCO2"] if result else 0
        total_points = result[0]["totalPoints"] if result else 0
        
        return {
            "success": True,
            "stats": {
                "totalUsers": total_users,
                "totalPosts": total_posts,
                "pendingPosts": pending_posts,
                "approvedPosts": approved_posts,
                "rejectedPosts": rejected_posts,
                "totalCO2Offset": round(total_co2, 2),
                "totalEcoPoints": total_points
            }
        }
    except Exception as e:
        logger.error(f"Error fetching admin stats: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch stats")
