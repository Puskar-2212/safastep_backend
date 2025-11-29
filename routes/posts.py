from fastapi import APIRouter, HTTPException, File, UploadFile, Form
from bson import ObjectId
import os
import time
import shutil
import logging
from database import users_collection, posts_collection
from config import UPLOAD_DIR, BASE_URL

logger = logging.getLogger(__name__)
router = APIRouter()

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
        
        image_url = f"{BASE_URL}/uploads/{unique_filename}"
        
        post_data = {
            "mobile": mobile,
            "userName": f"{user['firstName']} {user['lastName']}",
            "userProfilePicture": user.get("profilePicture", None),
            "caption": caption,
            "category": category,
            "categoryId": categoryId,
            "imageUrl": image_url,
            "imageFilename": unique_filename,
            "likes": [],
            "likesCount": 0,
            "comments": [],
            "commentsCount": 0,
            "createdAt": time.time(),
            "updatedAt": time.time()
        }
        
        result = posts_collection.insert_one(post_data)
        post_data["_id"] = str(result.inserted_id)
        
        logger.info(f"Post created by user: {mobile}")
        
        return {
            "success": True,
            "message": "Post created successfully",
            "post": post_data
        }
        
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
async def delete_post(post_id: str, mobile: str):
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
