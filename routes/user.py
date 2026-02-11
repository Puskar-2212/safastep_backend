from fastapi import APIRouter, HTTPException, File, UploadFile, Form
import os
import time
import shutil
import logging
from database import users_collection
from config import UPLOAD_DIR, BASE_URL
from utils.face_verifier_opencv import FaceVerifier

# Configure logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

router = APIRouter()

# Initialize face verifier
face_verifier = FaceVerifier()

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

@router.get("/user/by-identifier/{identifier}")
async def get_user_by_identifier(identifier: str):
    """
    Get user by mobile number or email
    """
    # Try to find by mobile first
    user = users_collection.find_one({"mobile": identifier})
    
    # If not found, try by email
    if not user:
        user = users_collection.find_one({"email": identifier})
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    
    user["_id"] = str(user["_id"])
    
    return {
        "success": True,
        "user": {
            "mobile": user.get("mobile"),
            "email": user.get("email"),
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
async def upload_profile_picture(file: UploadFile = File(...), mobile: str = Form(None), email: str = Form(None)):
    try:
        logger.info(f"Upload request received - mobile: {mobile}, email: {email}, file: {file.filename if file else 'None'}")
        logger.info(f"File content type: {file.content_type if file else 'None'}")
        
        if not file.content_type.startswith('image/'):
            logger.error(f"Invalid file type: {file.content_type}")
            raise HTTPException(status_code=400, detail="File must be an image")
        
        # Find user by mobile or email
        if mobile:
            logger.info(f"Looking up user by mobile: {mobile}")
            user = users_collection.find_one({"mobile": mobile})
            identifier = mobile
        elif email:
            logger.info(f"Looking up user by email: {email}")
            user = users_collection.find_one({"email": email})
            identifier = email
        else:
            logger.error("Neither mobile nor email provided")
            raise HTTPException(status_code=400, detail="Either mobile or email must be provided")
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        file_extension = file.filename.split('.')[-1]
        unique_filename = f"profile_{identifier.replace('@', '_').replace('.', '_')}_{int(time.time())}.{file_extension}"
        file_path = os.path.join(UPLOAD_DIR, unique_filename)
        
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Extract face encoding from profile picture
        logger.info(f"Extracting face encoding for user: {identifier}")
        face_result = face_verifier.extract_face_encoding(file_path)
        
        if not face_result["success"]:
            # Delete uploaded file if face extraction fails
            if os.path.exists(file_path):
                os.remove(file_path)
            raise HTTPException(
                status_code=400, 
                detail=face_result.get("error", "Failed to detect face in image. Please use a clear photo of your face.")
            )
        
        profile_picture_url = f"{BASE_URL}/uploads/{unique_filename}"
        
        # Update user with profile picture and face encoding
        query = {"mobile": mobile} if mobile else {"email": email}
        users_collection.update_one(
            query,
            {
                "$set": {
                    "profilePicture": profile_picture_url,
                    "profilePictureFilename": unique_filename,
                    "faceEncoding": face_result["face_encoding"],
                    "faceVerified": True,
                    "updatedAt": time.time()
                }
            }
        )
        
        logger.info(f"Profile picture and face encoding saved for user: {identifier}")
        
        return {
            "success": True,
            "message": "Profile picture uploaded and face verified successfully",
            "profilePictureUrl": profile_picture_url,
            "faceVerified": True
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading profile picture: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to upload profile picture: {str(e)}")

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

@router.put("/update-profile")
async def update_profile(mobile: str = Form(None), email: str = Form(None), 
                        firstName: str = Form(...), lastName: str = Form(...), 
                        dateOfBirth: str = Form(...)):
    try:
        logger.info(f"Update profile request - mobile: {mobile}, email: {email}")
        
        # Find user by mobile or email
        if mobile:
            user = users_collection.find_one({"mobile": mobile})
            identifier = mobile
            query = {"mobile": mobile}
        elif email:
            user = users_collection.find_one({"email": email})
            identifier = email
            query = {"email": email}
        else:
            raise HTTPException(status_code=400, detail="Either mobile or email must be provided")
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Parse dateOfBirth (expecting JSON string)
        import json
        try:
            dob = json.loads(dateOfBirth)
        except:
            raise HTTPException(status_code=400, detail="Invalid date of birth format")
        
        # Update user profile
        users_collection.update_one(
            query,
            {
                "$set": {
                    "firstName": firstName,
                    "lastName": lastName,
                    "dateOfBirth": dob,
                    "updatedAt": time.time()
                }
            }
        )
        
        logger.info(f"Profile updated for user: {identifier}")
        
        # Get updated user data
        updated_user = users_collection.find_one(query)
        updated_user["_id"] = str(updated_user["_id"])
        
        return {
            "success": True,
            "message": "Profile updated successfully",
            "user": {
                "mobile": updated_user.get("mobile"),
                "email": updated_user.get("email"),
                "firstName": updated_user["firstName"],
                "lastName": updated_user["lastName"],
                "dateOfBirth": updated_user["dateOfBirth"],
                "profilePicture": updated_user.get("profilePicture"),
                "carbonFootprint": updated_user.get("carbonFootprint", 0),
                "stepsCount": updated_user.get("stepsCount", 0),
                "createdAt": updated_user["createdAt"]
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating profile: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to update profile: {str(e)}")
