from fastapi import APIRouter, HTTPException, File, UploadFile, Form, Query
from bson import ObjectId
import os
import time
import shutil
import logging
from database import users_collection, posts_collection
from config import UPLOAD_DIR, BASE_URL
from utils.image_verification import ImageVerificationService

logger = logging.getLogger(__name__)
router = APIRouter()

# Initialize verification service
verification_service = ImageVerificationService()

# CO2 Offset and Eco Points calculation
def calculate_eco_impact(category: str, verification_score: float) -> tuple:
    """
    Calculate eco points and CO2 offset based on category and verification score
    Returns: (eco_points, co2_offset_kg)
    """
    # Base values per category (CO2 in kg)
    category_impacts = {
        "plantation": {"co2": 21.0, "points": 100},  # 1 tree absorbs ~21kg CO2/year
        "recycling": {"co2": 5.0, "points": 50},     # Average recycling impact
        "transportation": {"co2": 2.5, "points": 40}, # Bike vs car for 10km
        "energy": {"co2": 3.0, "points": 60},         # Solar/renewable usage
        "energy_conservation": {"co2": 3.0, "points": 60},
        "waste_management": {"co2": 1.5, "points": 30},
        "waste-management": {"co2": 1.5, "points": 30},
    }
    
    # Get category impact (default if not found)
    category_key = category.lower().replace(" ", "_")
    impact = category_impacts.get(category_key, {"co2": 1.0, "points": 20})
    
    # Scale by verification score (50-100 score = 50-100% of impact)
    score_multiplier = max(0.5, min(1.0, verification_score / 100))
    
    eco_points = int(impact["points"] * score_multiplier)
    co2_offset = round(impact["co2"] * score_multiplier, 2)
    
    return eco_points, co2_offset

@router.post("/posts")
async def create_post(
    mobile: str = Form(...),
    caption: str = Form(...),
    category: str = Form(...),
    categoryId: str = Form(...),
    image: UploadFile = File(...)
):
    try:
        if not image.content_type.startswith('image/'):
            raise HTTPException(status_code=400, detail="File must be an image")
        
        user = users_collection.find_one({"mobile": mobile})
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        file_extension = image.filename.split('.')[-1]
        unique_filename = f"post_{mobile}_{int(time.time())}.{file_extension}"
        file_path = os.path.join(UPLOAD_DIR, unique_filename)
        
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(image.file, buffer)
        
        # AI Verification Pipeline
        logger.info(f"Starting AI verification for image: {unique_filename}")
        verification_result = verification_service.verify_image(file_path, category, mobile)
        
        # Check if image is approved
        if not verification_result["approved"]:
            # Delete the uploaded file if rejected
            if os.path.exists(file_path):
                os.remove(file_path)
            
            status = verification_result.get("status", "rejected")
            reasons = verification_result.get("reasons", ["Verification failed"])
            score = verification_result["overall_score"]
            
            # Format error message
            reasons_text = "\n• ".join(reasons)
            error_message = f"Image verification failed (Score: {score}/100)\n\nReasons:\n• {reasons_text}"
            
            raise HTTPException(
                status_code=400,
                detail=error_message
            )
        
        image_url = f"{BASE_URL}/uploads/{unique_filename}"
        
        # Calculate Eco Points and CO2 Offset based on category
        eco_points, co2_offset = calculate_eco_impact(category, verification_result["overall_score"])
        
        post_data = {
            "mobile": mobile,
            "userName": f"{user['firstName']} {user['lastName']}",
            "userProfilePicture": user.get("profilePicture", None),
            "caption": caption,
            "category": category,
            "categoryId": categoryId,
            "imageUrl": image_url,
            "imageFilename": unique_filename,
            "imageHash": verification_result["image_hash"],
            "verificationScore": verification_result["overall_score"],
            "verificationStatus": verification_result["status"],
            "detectedObjects": verification_result.get("category_verification", {}).get("matched_objects", []),
            "ecoPoints": eco_points,
            "co2Offset": co2_offset,  # in kg
            "likes": [],
            "likesCount": 0,
            "comments": [],
            "commentsCount": 0,
            "createdAt": time.time(),
            "updatedAt": time.time()
        }
        
        result = posts_collection.insert_one(post_data)
        post_data["_id"] = str(result.inserted_id)
        
        # Update user's total eco points and CO2 offset
        users_collection.update_one(
            {"mobile": mobile},
            {
                "$inc": {
                    "ecoPoints": eco_points,
                    "totalCO2Offset": co2_offset
                }
            }
        )
        
        logger.info(f"Post created by {mobile}: +{eco_points} points, {co2_offset}kg CO2 offset")
        
        return {
            "success": True,
            "message": "Post created successfully",
            "post": post_data,
            "rewards": {
                "ecoPoints": eco_points,
                "co2Offset": co2_offset
            }
        }
        
    except HTTPException:
        # Re-raise HTTPException (400, 404, etc.) without catching
        raise
    except Exception as e:
        logger.error(f"Error creating post: {e}")
        raise HTTPException(status_code=500, detail="Failed to create post")

@router.get("/posts")
async def get_all_posts(skip: int = 0, limit: int = 20):
    try:
        posts = list(posts_collection.find().sort("createdAt", -1).skip(skip).limit(limit))
        
        for post in posts:
            post["_id"] = str(post["_id"])
        
        return {
            "success": True,
            "posts": posts,
            "count": len(posts)
        }
        
    except Exception as e:
        logger.error(f"Error fetching posts: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch posts")

@router.get("/posts/category/{category_id}")
async def get_posts_by_category(category_id: str, skip: int = 0, limit: int = 20):
    try:
        posts = list(posts_collection.find({"categoryId": category_id}).sort("createdAt", -1).skip(skip).limit(limit))
        
        for post in posts:
            post["_id"] = str(post["_id"])
        
        return {
            "success": True,
            "posts": posts,
            "count": len(posts)
        }
        
    except Exception as e:
        logger.error(f"Error fetching posts by category: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch posts")

@router.get("/posts/user/{mobile}")
async def get_user_posts(mobile: str, skip: int = 0, limit: int = 20):
    try:
        posts = list(posts_collection.find({"mobile": mobile}).sort("createdAt", -1).skip(skip).limit(limit))
        
        for post in posts:
            post["_id"] = str(post["_id"])
        
        return {
            "success": True,
            "posts": posts,
            "count": len(posts)
        }
        
    except Exception as e:
        logger.error(f"Error fetching user posts: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch user posts")

@router.get("/posts/{post_id}")
async def get_post(post_id: str):
    try:
        post = posts_collection.find_one({"_id": ObjectId(post_id)})
        
        if not post:
            raise HTTPException(status_code=404, detail="Post not found")
        
        post["_id"] = str(post["_id"])
        
        return {
            "success": True,
            "post": post
        }
        
    except Exception as e:
        logger.error(f"Error fetching post: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch post")

@router.post("/posts/{post_id}/like")
async def toggle_like(post_id: str, mobile: str = Form(...)):
    try:
        post = posts_collection.find_one({"_id": ObjectId(post_id)})
        
        if not post:
            raise HTTPException(status_code=404, detail="Post not found")
        
        likes = post.get("likes", [])
        
        if mobile in likes:
            posts_collection.update_one(
                {"_id": ObjectId(post_id)},
                {
                    "$pull": {"likes": mobile},
                    "$inc": {"likesCount": -1},
                    "$set": {"updatedAt": time.time()}
                }
            )
            liked = False
        else:
            posts_collection.update_one(
                {"_id": ObjectId(post_id)},
                {
                    "$push": {"likes": mobile},
                    "$inc": {"likesCount": 1},
                    "$set": {"updatedAt": time.time()}
                }
            )
            liked = True
        
        updated_post = posts_collection.find_one({"_id": ObjectId(post_id)})
        
        return {
            "success": True,
            "liked": liked,
            "likesCount": updated_post.get("likesCount", 0)
        }
        
    except Exception as e:
        logger.error(f"Error toggling like: {e}")
        raise HTTPException(status_code=500, detail="Failed to toggle like")

@router.delete("/posts/{post_id}")
async def delete_post(post_id: str, mobile: str = Query(...)):
    try:
        post = posts_collection.find_one({"_id": ObjectId(post_id)})
        
        if not post:
            raise HTTPException(status_code=404, detail="Post not found")
        
        if post["mobile"] != mobile:
            raise HTTPException(status_code=403, detail="Not authorized to delete this post")
        
        if "imageFilename" in post:
            file_path = os.path.join(UPLOAD_DIR, post["imageFilename"])
            if os.path.exists(file_path):
                os.remove(file_path)
        
        posts_collection.delete_one({"_id": ObjectId(post_id)})
        
        logger.info(f"Post deleted: {post_id}")
        
        return {
            "success": True,
            "message": "Post deleted successfully"
        }
        
    except Exception as e:
        logger.error(f"Error deleting post: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete post")
