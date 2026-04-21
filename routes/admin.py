from fastapi import APIRouter, HTTPException, Query, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import Optional
from database import users_collection, posts_collection, likes_collection, eco_locations_collection
import logging
from bson import ObjectId
import jwt
import os

logger = logging.getLogger(__name__)
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
# Authentication is handled by admin_auth.py

@router.get("/admin/users")
async def get_all_users(
    skip: int = Query(0, ge=0), 
    limit: int = Query(10, ge=1, le=100),
    admin_data: dict = Depends(verify_admin_token)
):
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
        
        # Get user identifier (mobile or email)
        identifier = user.get("mobile") or user.get("email")
        
        # Get user's posts count
        posts_count = posts_collection.count_documents({
            "$or": [
                {"identifier": identifier},
                {"mobile": identifier},
                {"email": identifier}
            ]
        })
        
        # Get user's posts IDs
        user_posts = list(posts_collection.find(
            {
                "$or": [
                    {"identifier": identifier},
                    {"mobile": identifier},
                    {"email": identifier}
                ]
            },
            {"_id": 1}
        ))
        user_post_ids = [str(post["_id"]) for post in user_posts]
        
        # Count total likes on user's posts
        likes_count = likes_collection.count_documents({
            "postId": {"$in": user_post_ids}
        })
        
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
    """Get all posts with pagination - excludes rejected posts and admin announcements"""
    try:
        # Only show approved and pending posts, exclude rejected posts and admin announcements
        filter_query = {
            "isAdminPost": {"$ne": True},  # Exclude admin announcements
            "verificationStatus": {"$in": ["approved", "pending_review", "error"]}  # Exclude rejected
        }
        
        total = posts_collection.count_documents(filter_query)
        posts = list(posts_collection.find(filter_query).sort("_id", -1).skip(skip).limit(limit))
        
        # Convert ObjectId to string and format data
        for post in posts:
            post_id = str(post["_id"])
            post["_id"] = post_id
            if "createdAt" in post:
                post["createdAt"] = int(post["createdAt"])
            
            # Count actual likes from likes collection
            likes_count = likes_collection.count_documents({"postId": post_id})
            post["likesCount"] = likes_count
            
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
    """Search posts by caption or user name - excludes rejected posts and admin announcements"""
    try:
        # Escape special regex characters
        import re
        escaped_query = re.escape(query)
        
        search_filter = {
            "isAdminPost": {"$ne": True},  # Exclude admin announcements
            "verificationStatus": {"$in": ["approved", "pending_review", "error"]},  # Exclude rejected
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
            post_id = str(post["_id"])
            post["_id"] = post_id
            if "createdAt" in post:
                post["createdAt"] = int(post["createdAt"])
            
            # Count actual likes from likes collection
            likes_count = likes_collection.count_documents({"postId": post_id})
            post["likesCount"] = likes_count
            
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
async def get_pending_posts(skip: int = Query(0, ge=0), limit: int = Query(10, ge=1, le=100), admin_data: dict = Depends(verify_admin_token)):
    """Get all posts pending admin review with AI analysis summary"""
    try:
        # Find posts with pending_review OR error status
        total = posts_collection.count_documents({
            "verificationStatus": {"$in": ["pending_review", "error"]}
        })
        posts = list(posts_collection.find(
            {"verificationStatus": {"$in": ["pending_review", "error"]}}
        ).sort("createdAt", -1).skip(skip).limit(limit))
        
        # Convert ObjectId to string and enrich with user data and AI analysis
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
            
            # Add AI analysis summary
            ai_verification = post.get("aiVerification", {})
            face_verification = post.get("faceVerification", {})
            
            # Extract data from the actual stored structure
            quality_check = ai_verification.get("qualityCheck", {})
            category_verification = ai_verification.get("categoryVerification", {})
            duplicate_check = ai_verification.get("duplicateCheck", {})
            
            face_confidence = face_verification.get("confidence", 0)
            quality_score = quality_check.get("quality_score", 0)
            matched_objects = ai_verification.get("matchedObjects", [])
            object_detected = len(matched_objects) > 0
            is_duplicate = duplicate_check.get("is_duplicate", False)
            
            # Calculate AI recommendation
            ai_recommendation = "manual_review"
            if face_confidence >= 90 and object_detected and quality_score >= 80 and not is_duplicate:
                ai_recommendation = "auto_approve"
            elif face_confidence < 30 or not object_detected or quality_score < 20 or is_duplicate:
                ai_recommendation = "auto_reject"
            
            post["ai_summary"] = {
                "face_confidence": face_confidence,
                "object_detected": object_detected,
                "quality_score": quality_score,
                "is_duplicate": is_duplicate,
                "ai_recommendation": ai_recommendation,
                "confidence_level": "high" if face_confidence >= 80 else "medium" if face_confidence >= 50 else "low",
                "matched_objects": matched_objects,
                "detected_objects": ai_verification.get("detectedObjects", [])
            }
        
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

class DeletePostRequest(BaseModel):
    reason: str = "Violated community guidelines"

@router.delete("/admin/posts/{post_id}")
async def delete_post(post_id: str, request: DeletePostRequest):
    """Delete a post and all associated likes with reason"""
    try:
        from bson import ObjectId
        from routes.notifications import create_notification
        
        post = posts_collection.find_one({"_id": ObjectId(post_id)})
        
        if not post:
            raise HTTPException(status_code=404, detail="Post not found")
        
        # Get user identifier before deleting
        user_identifier = post.get("identifier") or post.get("mobile") or post.get("email")
        post_caption = post.get("caption", "your post")[:50]  # First 50 chars
        deletion_reason = request.reason or "Violated community guidelines"
        
        # Delete post's likes
        likes_deleted = likes_collection.delete_many({"postId": post_id})
        
        # Delete post
        posts_collection.delete_one({"_id": ObjectId(post_id)})
        
        # Send notification to user with reason
        if user_identifier:
            create_notification(
                user_id=user_identifier,
                notification_type="post_deleted",
                title="Post Removed",
                message=f"Your post \"{post_caption}...\" was removed.\n\nReason: {deletion_reason}",
                data={
                    "postId": post_id,
                    "caption": post_caption,
                    "reason": deletion_reason
                }
            )
        
        logger.info(f"Post {post_id} deleted by admin. Reason: {deletion_reason}. Likes: {likes_deleted.deleted_count}. User notified: {user_identifier}")
        
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
    """Create a new eco-location and notify all users"""
    try:
        from routes.notifications import create_notification
        
        location_data = location.dict()
        result = eco_locations_collection.insert_one(location_data)
        location_id = str(result.inserted_id)
        
        # Send notification to all users about the new eco-location
        try:
            all_users = users_collection.find({}, {"mobile": 1, "email": 1})
            notification_count = 0
            
            for user in all_users:
                user_identifier = user.get("mobile") or user.get("email")
                if user_identifier:
                    create_notification(
                        user_id=user_identifier,
                        notification_type="new_eco_location",
                        title=f"New Eco-Location: {location.name}",
                        message=f"Discover {location.name} - a new {location.category.replace('-', ' ')} added to the map! Check it out and plan your eco-friendly visit.",
                        data={
                            "locationId": location_id,
                            "locationName": location.name,
                            "category": location.category,
                            "latitude": location.latitude,
                            "longitude": location.longitude
                        }
                    )
                    notification_count += 1
            
            logger.info(f"Sent {notification_count} notifications for new eco-location {location_id}")
        except Exception as e:
            logger.error(f"Error sending notifications for eco-location: {e}")
            # Don't fail the location creation if notifications fail
        
        return {
            "success": True,
            "message": "Eco-location created successfully",
            "location_id": location_id,
            "notificationsSent": notification_count if 'notification_count' in locals() else 0
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
async def get_post_review_details(post_id: str, admin_data: dict = Depends(verify_admin_token)):
    """Get detailed information for post review including user profile and AI analysis"""
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
        
        # Extract AI analysis results from post
        ai_verification = post.get("aiVerification", {})
        face_verification = post.get("faceVerification", {})
        
        # Extract data from the actual stored structure
        quality_check = ai_verification.get("qualityCheck", {})
        category_verification = ai_verification.get("categoryVerification", {})
        duplicate_check = ai_verification.get("duplicateCheck", {})
        
        ai_analysis = {
            "face_verification": face_verification,
            "object_detection": {
                "verified": category_verification.get("verified", False),
                "matchedObjects": ai_verification.get("matchedObjects", []),
                "detectedObjects": ai_verification.get("detectedObjects", []),
                "score": category_verification.get("score", 0)
            },
            "image_quality": quality_check,
            "duplicate_check": duplicate_check,
            "overall_score": post.get("verificationScore", 0),
            "verification_status": post.get("verificationStatus", "unknown")
        }
        
        # Calculate confidence levels
        face_confidence = face_verification.get("confidence", 0)
        quality_score = quality_check.get("quality_score", 0)
        matched_objects = ai_verification.get("matchedObjects", [])
        object_detected = len(matched_objects) > 0
        is_duplicate = duplicate_check.get("is_duplicate", False)
        
        # Determine overall AI recommendation
        ai_recommendation = "manual_review"
        if face_confidence >= 90 and object_detected and quality_score >= 80 and not is_duplicate:
            ai_recommendation = "auto_approve"
        elif face_confidence < 30 or not object_detected or quality_score < 20 or is_duplicate:
            ai_recommendation = "auto_reject"
        
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
            } if user else None,
            "ai_analysis": {
                **ai_analysis,
                "ai_recommendation": ai_recommendation,
                "confidence_level": "high" if face_confidence >= 80 else "medium" if face_confidence >= 50 else "low",
                "quality_level": "good" if quality_score >= 70 else "fair" if quality_score >= 40 else "poor",
                "face_confidence": face_confidence,
                "object_detected": object_detected,
                "quality_score": quality_score,
                "is_duplicate": is_duplicate,
                "matched_objects": matched_objects
            }
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
        from routes.notifications import create_notification
        
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
            
            # Create notification for user
            create_notification(
                user_id=identifier,
                notification_type="post_approved",
                title="Post Approved",
                message=f"Your post was approved! You earned {eco_points} eco points and offset {co2_offset}kg CO2.",
                data={
                    "postId": post_id,
                    "ecoPoints": eco_points,
                    "co2Offset": co2_offset
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
    """Reject a pending post and delete it"""
    try:
        import time
        import os
        from config import UPLOAD_DIR
        from utils.cloudinary_upload import delete_image_from_cloudinary
        from routes.notifications import create_notification
        
        post = posts_collection.find_one({"_id": ObjectId(post_id)})
        
        if not post:
            raise HTTPException(status_code=404, detail="Post not found")
        
        if post.get("verificationStatus") != "pending_review":
            raise HTTPException(status_code=400, detail="Post is not pending review")
        
        # Get user identifier before deleting
        identifier = post.get("identifier") or post.get("mobile") or post.get("email")
        
        # Delete image from Cloudinary
        cloudinary_public_id = post.get("cloudinaryPublicId")
        if cloudinary_public_id:
            delete_result = delete_image_from_cloudinary(cloudinary_public_id)
            if delete_result["success"]:
                logger.info(f"Deleted image from Cloudinary: {cloudinary_public_id}")
        
        # Also delete local file if it exists (for backward compatibility)
        if "imageFilename" in post:
            file_path = os.path.join(UPLOAD_DIR, post["imageFilename"])
            if os.path.exists(file_path):
                os.remove(file_path)
                logger.info(f"Deleted local image file: {post['imageFilename']}")
        
        # Delete the post completely instead of marking as rejected
        posts_collection.delete_one({"_id": ObjectId(post_id)})
        
        # Create notification for user
        if identifier:
            create_notification(
                user_id=identifier,
                notification_type="post_rejected",
                title="Post Rejected",
                message=f"Your post was rejected. Reason: {request.reason}",
                data={
                    "postId": post_id,
                    "reason": request.reason,
                    "notes": request.notes
                }
            )
        
        logger.info(f"Post {post_id} rejected and deleted by admin {request.adminId}. Reason: {request.reason}")
        
        return {
            "success": True,
            "message": "Post rejected and deleted successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error rejecting post: {e}")
        raise HTTPException(status_code=500, detail="Failed to reject post")


@router.get("/admin/stats")
async def get_admin_stats(admin_data: dict = Depends(verify_admin_token)):
    """Get admin dashboard statistics"""
    try:
        total_users = users_collection.count_documents({})
        total_posts = posts_collection.count_documents({})
        pending_posts = posts_collection.count_documents({
            "verificationStatus": {"$in": ["pending_review", "error"]}
        })
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


@router.get("/admin/growth-data")
async def get_growth_data(months: int = Query(6, ge=1, le=12), admin_data: dict = Depends(verify_admin_token)):
    """Get historical growth data for users and posts by month"""
    try:
        import time
        from datetime import datetime, timedelta
        
        # Calculate the start date (X months ago)
        now = datetime.now()
        start_date = now - timedelta(days=months * 30)
        start_timestamp = start_date.timestamp()
        
        # Get monthly user registrations
        user_pipeline = [
            {"$match": {"createdAt": {"$exists": True}}},
            {"$project": {
                "year": {"$year": {"$toDate": {"$multiply": ["$createdAt", 1000]}}},
                "month": {"$month": {"$toDate": {"$multiply": ["$createdAt", 1000]}}}
            }},
            {"$group": {
                "_id": {"year": "$year", "month": "$month"},
                "count": {"$sum": 1}
            }},
            {"$sort": {"_id.year": 1, "_id.month": 1}}
        ]
        
        # Get monthly post creations (approved posts only)
        post_pipeline = [
            {"$match": {
                "createdAt": {"$exists": True},
                "verificationStatus": "approved"
            }},
            {"$project": {
                "year": {"$year": {"$toDate": {"$multiply": ["$createdAt", 1000]}}},
                "month": {"$month": {"$toDate": {"$multiply": ["$createdAt", 1000]}}}
            }},
            {"$group": {
                "_id": {"year": "$year", "month": "$month"},
                "count": {"$sum": 1}
            }},
            {"$sort": {"_id.year": 1, "_id.month": 1}}
        ]
        
        user_results = list(users_collection.aggregate(user_pipeline))
        post_results = list(posts_collection.aggregate(post_pipeline))
        
        # Create a dictionary for easy lookup
        user_by_month = {f"{r['_id']['year']}-{r['_id']['month']:02d}": r['count'] for r in user_results}
        post_by_month = {f"{r['_id']['year']}-{r['_id']['month']:02d}": r['count'] for r in post_results}
        
        # Generate data for the last X months
        growth_data = []
        cumulative_users = 0
        cumulative_posts = 0
        
        for i in range(months):
            date = now - timedelta(days=(months - i - 1) * 30)
            month_key = f"{date.year}-{date.month:02d}"
            month_name = date.strftime("%b")
            
            # Get counts for this month
            users_this_month = user_by_month.get(month_key, 0)
            posts_this_month = post_by_month.get(month_key, 0)
            
            # Add to cumulative totals
            cumulative_users += users_this_month
            cumulative_posts += posts_this_month
            
            growth_data.append({
                "month": month_name,
                "year": date.year,
                "users": cumulative_users,
                "posts": cumulative_posts,
                "newUsers": users_this_month,
                "newPosts": posts_this_month
            })
        
        # Calculate growth percentages (comparing last month to previous month)
        user_growth = 0
        post_growth = 0
        
        if len(growth_data) >= 2:
            prev_users = growth_data[-2]["users"]
            curr_users = growth_data[-1]["users"]
            if prev_users > 0:
                user_growth = round(((curr_users - prev_users) / prev_users) * 100, 1)
            
            prev_posts = growth_data[-2]["posts"]
            curr_posts = growth_data[-1]["posts"]
            if prev_posts > 0:
                post_growth = round(((curr_posts - prev_posts) / prev_posts) * 100, 1)
        
        return {
            "success": True,
            "growthData": growth_data,
            "trends": {
                "userGrowth": user_growth,
                "postGrowth": post_growth
            }
        }
    except Exception as e:
        logger.error(f"Error fetching growth data: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch growth data")


# Admin Announcement Posts
class AnnouncementPost(BaseModel):
    title: str
    description: str
    postType: str  # "news", "event", "tip", "alert"
    imageUrl: Optional[str] = None
    linkedLocationId: Optional[str] = None
    eventDate: Optional[str] = None
    eventTime: Optional[str] = None
    externalLink: Optional[str] = None
    isPinned: bool = False

class AnnouncementPostUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    postType: Optional[str] = None
    imageUrl: Optional[str] = None
    linkedLocationId: Optional[str] = None
    eventDate: Optional[str] = None
    eventTime: str = None
    externalLink: str = None
    isPinned: bool = None

@router.post("/admin/announcements")
async def create_announcement(announcement: AnnouncementPost, admin_data: dict = Depends(verify_admin_token)):
    """Create an admin announcement post and notify all users"""
    try:
        import time
        from routes.notifications import create_notification
        
        # Debug logging
        logger.info(f"Received announcement data: {announcement.dict()}")
        
        # Validate linked location if provided
        if announcement.linkedLocationId and announcement.linkedLocationId.strip():
            try:
                location = eco_locations_collection.find_one({"_id": ObjectId(announcement.linkedLocationId)})
                if not location:
                    raise HTTPException(status_code=404, detail="Linked location not found")
            except Exception as e:
                logger.error(f"Invalid location ID: {announcement.linkedLocationId} - {e}")
                raise HTTPException(status_code=400, detail=f"Invalid location ID format: {announcement.linkedLocationId}")
        
        announcement_doc = {
            "title": announcement.title,
            "description": announcement.description,
            "postType": announcement.postType,
            "imageUrl": announcement.imageUrl,
            "linkedLocationId": announcement.linkedLocationId if announcement.linkedLocationId and announcement.linkedLocationId.strip() else None,
            "eventDate": announcement.eventDate,
            "eventTime": announcement.eventTime,
            "externalLink": announcement.externalLink,
            "isPinned": announcement.isPinned,
            "isAdminPost": True,
            "createdBy": admin_data["username"],
            "createdAt": time.time(),
            "updatedAt": time.time(),
            "views": 0
        }
        
        result = posts_collection.insert_one(announcement_doc)
        announcement_id = str(result.inserted_id)
        
        # Send notification to all users
        try:
            # Get all users
            all_users = users_collection.find({}, {"mobile": 1, "email": 1})
            notification_count = 0
            
            for user in all_users:
                user_identifier = user.get("mobile") or user.get("email")
                if user_identifier:
                    # Create notification for each user
                    create_notification(
                        user_id=user_identifier,
                        notification_type="announcement",
                        title=f" New {announcement.postType.title()}: {announcement.title}",
                        message=announcement.description[:100] + ("..." if len(announcement.description) > 100 else ""),
                        data={
                            "announcementId": announcement_id,
                            "postType": announcement.postType,
                            "eventDate": announcement.eventDate,
                            "eventTime": announcement.eventTime
                        }
                    )
                    notification_count += 1
            
            logger.info(f"Sent {notification_count} notifications for announcement {announcement_id}")
        except Exception as e:
            logger.error(f"Error sending notifications for announcement: {e}")
            # Don't fail the announcement creation if notifications fail
        
        logger.info(f"Admin announcement created by {admin_data['username']}: {result.inserted_id}")
        
        return {
            "success": True,
            "message": "Announcement created successfully",
            "announcementId": announcement_id,
            "notificationsSent": notification_count if 'notification_count' in locals() else 0
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating announcement: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create announcement: {str(e)}")

@router.get("/admin/announcements")
async def get_all_announcements(
    skip: int = Query(0, ge=0), 
    limit: int = Query(10, ge=1, le=100),
    admin_data: dict = Depends(verify_admin_token)
):
    """Get all admin announcements"""
    try:
        total = posts_collection.count_documents({"isAdminPost": True})
        announcements = list(posts_collection.find(
            {"isAdminPost": True}
        ).sort([("isPinned", -1), ("createdAt", -1)]).skip(skip).limit(limit))
        
        # Enrich with location data
        for announcement in announcements:
            announcement["_id"] = str(announcement["_id"])
            
            if announcement.get("linkedLocationId"):
                location = eco_locations_collection.find_one({"_id": ObjectId(announcement["linkedLocationId"])})
                if location:
                    location["_id"] = str(location["_id"])
                    announcement["linkedLocation"] = location
        
        return {
            "success": True,
            "total": total,
            "skip": skip,
            "limit": limit,
            "announcements": announcements
        }
    except Exception as e:
        logger.error(f"Error fetching announcements: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch announcements")

@router.get("/admin/announcements/{announcement_id}")
async def get_announcement_details(announcement_id: str, admin_data: dict = Depends(verify_admin_token)):
    """Get announcement details"""
    try:
        announcement = posts_collection.find_one({
            "_id": ObjectId(announcement_id),
            "isAdminPost": True
        })
        
        if not announcement:
            raise HTTPException(status_code=404, detail="Announcement not found")
        
        announcement["_id"] = str(announcement["_id"])
        
        # Get linked location if exists
        if announcement.get("linkedLocationId"):
            location = eco_locations_collection.find_one({"_id": ObjectId(announcement["linkedLocationId"])})
            if location:
                location["_id"] = str(location["_id"])
                announcement["linkedLocation"] = location
        
        return {
            "success": True,
            "announcement": announcement
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching announcement details: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch announcement details")

@router.put("/admin/announcements/{announcement_id}")
async def update_announcement(
    announcement_id: str, 
    announcement: AnnouncementPostUpdate,
    admin_data: dict = Depends(verify_admin_token)
):
    """Update an announcement"""
    try:
        import time
        
        update_data = {k: v for k, v in announcement.dict().items() if v is not None}
        
        if not update_data:
            raise HTTPException(status_code=400, detail="No fields to update")
        
        # Validate linked location if provided
        if "linkedLocationId" in update_data and update_data["linkedLocationId"]:
            location = eco_locations_collection.find_one({"_id": ObjectId(update_data["linkedLocationId"])})
            if not location:
                raise HTTPException(status_code=404, detail="Linked location not found")
        
        update_data["updatedAt"] = time.time()
        
        result = posts_collection.update_one(
            {"_id": ObjectId(announcement_id), "isAdminPost": True},
            {"$set": update_data}
        )
        
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Announcement not found")
        
        logger.info(f"Announcement {announcement_id} updated by {admin_data['username']}")
        
        return {
            "success": True,
            "message": "Announcement updated successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating announcement: {e}")
        raise HTTPException(status_code=500, detail="Failed to update announcement")

@router.delete("/admin/announcements/{announcement_id}")
async def delete_announcement(announcement_id: str, admin_data: dict = Depends(verify_admin_token)):
    """Delete an announcement"""
    try:
        result = posts_collection.delete_one({
            "_id": ObjectId(announcement_id),
            "isAdminPost": True
        })
        
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Announcement not found")
        
        logger.info(f"Announcement {announcement_id} deleted by {admin_data['username']}")
        
        return {
            "success": True,
            "message": "Announcement deleted successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting announcement: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete announcement")

@router.post("/admin/announcements/{announcement_id}/pin")
async def toggle_pin_announcement(announcement_id: str, admin_data: dict = Depends(verify_admin_token)):
    """Toggle pin status of an announcement"""
    try:
        announcement = posts_collection.find_one({
            "_id": ObjectId(announcement_id),
            "isAdminPost": True
        })
        
        if not announcement:
            raise HTTPException(status_code=404, detail="Announcement not found")
        
        new_pin_status = not announcement.get("isPinned", False)
        
        posts_collection.update_one(
            {"_id": ObjectId(announcement_id)},
            {"$set": {"isPinned": new_pin_status}}
        )
        
        return {
            "success": True,
            "isPinned": new_pin_status,
            "message": f"Announcement {'pinned' if new_pin_status else 'unpinned'} successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error toggling pin: {e}")
        raise HTTPException(status_code=500, detail="Failed to toggle pin status")
