from fastapi import APIRouter, HTTPException, File, UploadFile, Form
import os
import time
import shutil
import logging
from database import users_collection
from config import UPLOAD_DIR, BASE_URL

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/user/{mobile}")
async def get_user_profile(mobile: str):
    user = users_collection.find_one({"mobile": mobile})
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    
    user["_id"] = str(user["_id"])
    
    return {
        "success": True,
        "user": {
            "mobile": user["mobile"],
            "firstName": user["firstName"],
            "lastName": user["lastName"],
            "dateOfBirth": user["dateOfBirth"],
            "carbonFootprint": user.get("carbonFootprint", 0),
            "stepsCount": user.get("stepsCount", 0),
            "profilePicture": user.get("profilePicture", None),
            "createdAt": user["createdAt"]
        }
    }

@router.post("/update-steps")
async def update_steps(mobile: str, steps: int):
    user = users_collection.find_one({"mobile": mobile})
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    
    distance_km = (steps * 0.000762)
    carbon_saved = distance_km * 0.04
    
    try:
        users_collection.update_one(
            {"mobile": mobile},
            {
                "$inc": {"stepsCount": steps},
                "$set": {
                    "carbonFootprint": user.get("carbonFootprint", 0) + carbon_saved,
                    "updatedAt": time.time()
                }
            }
        )
        
        return {
            "success": True,
            "message": "Steps updated successfully.",
            "carbonSaved": carbon_saved,
            "totalSteps": user.get("stepsCount", 0) + steps
        }
    except Exception as e:
        logger.error(f"Error updating steps: {e}")
        raise HTTPException(status_code=500, detail="Failed to update steps.")

@router.post("/upload-profile-picture")
async def upload_profile_picture(file: UploadFile = File(...), mobile: str = Form(...)):
    try:
        if not file.content_type.startswith('image/'):
            raise HTTPException(status_code=400, detail="File must be an image")
        
        user = users_collection.find_one({"mobile": mobile})
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        file_extension = file.filename.split('.')[-1]
        unique_filename = f"profile_{mobile}_{int(time.time())}.{file_extension}"
        file_path = os.path.join(UPLOAD_DIR, unique_filename)
        
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        profile_picture_url = f"{BASE_URL}/uploads/{unique_filename}"
        
        users_collection.update_one(
            {"mobile": mobile},
            {
                "$set": {
                    "profilePicture": profile_picture_url,
                    "profilePictureFilename": unique_filename,
                    "updatedAt": time.time()
                }
            }
        )
        
        logger.info(f"Profile picture uploaded for user: {mobile}")
        
        return {
            "success": True,
            "message": "Profile picture uploaded successfully",
            "profilePictureUrl": profile_picture_url
        }
        
    except Exception as e:
        logger.error(f"Error uploading profile picture: {e}")
        raise HTTPException(status_code=500, detail="Failed to upload profile picture")

@router.delete("/delete-profile-picture/{mobile}")
async def delete_profile_picture(mobile: str):
    try:
        user = users_collection.find_one({"mobile": mobile})
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        if "profilePictureFilename" in user:
            file_path = os.path.join(UPLOAD_DIR, user["profilePictureFilename"])
            if os.path.exists(file_path):
                os.remove(file_path)
        
        users_collection.update_one(
            {"mobile": mobile},
            {
                "$unset": {"profilePicture": "", "profilePictureFilename": ""},
                "$set": {"updatedAt": time.time()}
            }
        )
        
        logger.info(f"Profile picture deleted for user: {mobile}")
        
        return {"success": True, "message": "Profile picture deleted successfully"}
        
    except Exception as e:
        logger.error(f"Error deleting profile picture: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete profile picture")
