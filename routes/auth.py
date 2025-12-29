from fastapi import APIRouter, HTTPException
from twilio.rest import Client
import random
import time
import logging
from models import OTPRequest, VerifyOTP, SignupRequest, LoginRequest, VerifyPinResetOTP
from database import users_collection, posts_collection, carbon_footprints_collection
from config import TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_PHONE

logger = logging.getLogger(__name__)
router = APIRouter()

# Initialize Twilio client
twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

# In-memory storage for OTPs
otp_storage = {}

@router.post("/send-otp")
async def send_otp(request: OTPRequest):
    full_mobile = f"{request.countryCode}{request.mobile}"
    otp = str(random.randint(100000, 999999))
    otp_storage[full_mobile] = otp
 
    try:
        message = twilio_client.messages.create(
            body=f"Your SafaStep verification OTP is: {otp}. Every step reduces carbon!",
            from_=TWILIO_PHONE,
            to=full_mobile
        )
        logger.info(f"OTP sent to {full_mobile}: {otp}")
        logger.info(f"Twilio Message SID: {message.sid}")
        logger.info(f"Twilio Message Status: {message.status}")
        return {"success": True, "message": "OTP sent successfully."}
    except Exception as e:
        logger.error(f"Twilio error: {e}")
        raise HTTPException(status_code=500, detail="Failed to send OTP.")

@router.post("/verify-otp")
async def verify_otp(request: VerifyOTP):
    full_mobile = request.mobile
    stored_otp = otp_storage.get(full_mobile)

    if not stored_otp:
        logger.warning(f"No OTP found for {full_mobile}")
        raise HTTPException(status_code=400, detail="No OTP found for this mobile number.")
    
    if stored_otp != request.otp:
        logger.warning(f"Invalid OTP attempt for {full_mobile}")
        raise HTTPException(status_code=400, detail="Invalid OTP.")

    del otp_storage[full_mobile]
    logger.info(f"OTP verified for {full_mobile}")
    return {"success": True, "message": "OTP verified successfully."}

@router.post("/signup")
async def signup(request: SignupRequest):
    user_data = request.dict()
    
    user_exists = users_collection.find_one({"mobile": user_data["mobile"]})
    
    if user_exists:
        raise HTTPException(status_code=400, detail="Mobile number already registered.")

    user_data["createdAt"] = time.time()
    user_data["updatedAt"] = time.time()
    user_data["verified"] = True
    user_data["carbonFootprint"] = 0
    user_data["stepsCount"] = 0

    try:
        users_collection.insert_one(user_data)
        logger.info(f"User data saved for {user_data['mobile']}")
        return {"success": True, "message": "User registered successfully."}
    except Exception as e:
        logger.error(f"MongoDB error: {e}")
        raise HTTPException(status_code=500, detail="Failed to save user data.")

@router.post("/login")
async def login(request: LoginRequest):
    logger.info(f"Login request: mobile={request.mobile}")

    user = users_collection.find_one({
        "mobile": request.mobile, 
        "pin": request.pin
    })

    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    user["_id"] = str(user["_id"])
    logger.info(f"User logged in: {request.mobile}")
    
    return {
        "success": True, 
        "user": {
            "mobile": user["mobile"],
            "firstName": user["firstName"],
            "lastName": user["lastName"],
            "dateOfBirth": user["dateOfBirth"],
            "carbonFootprint": user.get("carbonFootprint", 0),
            "stepsCount": user.get("stepsCount", 0),
            "createdAt": user["createdAt"]
        }
    }

@router.post("/forgot-pin")
async def forgot_pin(request: OTPRequest):
    full_mobile = f"{request.countryCode}{request.mobile}"
    otp = str(random.randint(100000, 999999))
    otp_storage[full_mobile] = otp

    user_exists = users_collection.find_one({"mobile": full_mobile})

    if not user_exists:
        logger.warning(f"No user found for mobile: {full_mobile}")
        raise HTTPException(status_code=404, detail="Mobile number not registered.")

    try:
        message = twilio_client.messages.create(
            body=f"Your SafaStep PIN reset OTP is: {otp}",
            from_=TWILIO_PHONE,
            to=full_mobile
        )
        logger.info(f"OTP sent to {full_mobile} for PIN reset: {otp}")
        return {"success": True, "message": "OTP sent successfully for PIN reset."}
    except Exception as e:
        logger.error(f"Twilio error: {e}")
        raise HTTPException(status_code=500, detail="Failed to send OTP.")

@router.post("/verify-otp-pin-reset")
async def verify_otp_pin_reset(request: VerifyPinResetOTP):
    full_mobile = request.mobile
    stored_otp = otp_storage.get(full_mobile)

    if not stored_otp:
        logger.warning(f"No OTP found for {full_mobile}")
        raise HTTPException(status_code=400, detail="No OTP found for this mobile number.")
    
    if stored_otp != request.otp:
        logger.warning(f"Invalid OTP attempt for {full_mobile}")
        raise HTTPException(status_code=400, detail="Invalid OTP.")

    user = users_collection.find_one({"mobile": full_mobile})

    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    try:
        users_collection.update_one(
            {"mobile": full_mobile},
            {"$set": {"pin": request.new_pin, "updatedAt": time.time()}}
        )
        
        del otp_storage[full_mobile]
        logger.info(f"OTP verified and PIN reset for {full_mobile}")
        return {"success": True, "message": "PIN reset successfully."}
    except Exception as e:
        logger.error(f"Error resetting PIN: {e}")
        raise HTTPException(status_code=500, detail="Failed to reset PIN.")

@router.post("/change-pin")
async def change_pin(request: dict):
    mobile = request.get("mobile")
    current_pin = request.get("currentPin")
    new_pin = request.get("newPin")

    if not mobile or not current_pin or not new_pin:
        raise HTTPException(status_code=400, detail="Missing required fields")

    if len(new_pin) != 4 or not new_pin.isdigit():
        raise HTTPException(status_code=400, detail="PIN must be 4 digits")

    # Verify current PIN
    user = users_collection.find_one({"mobile": mobile, "pin": current_pin})

    if not user:
        raise HTTPException(status_code=401, detail="Current PIN is incorrect")

    # Update PIN
    try:
        users_collection.update_one(
            {"mobile": mobile},
            {"$set": {"pin": new_pin, "updatedAt": time.time()}}
        )
        logger.info(f"PIN changed successfully for {mobile}")
        return {"success": True, "message": "PIN changed successfully"}
    except Exception as e:
        logger.error(f"Error changing PIN: {e}")
        raise HTTPException(status_code=500, detail="Failed to change PIN")

@router.delete("/delete-account")
async def delete_account(request: dict):
    mobile = request.get("mobile")

    if not mobile:
        raise HTTPException(status_code=400, detail="Mobile number is required")

    user = users_collection.find_one({"mobile": mobile})

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    try:
        # Delete user from database
        users_collection.delete_one({"mobile": mobile})
        
        # Also delete user's posts and carbon footprint data
        posts_collection.delete_many({"mobile": mobile})
        carbon_footprints_collection.delete_many({"mobile": mobile})
        
        logger.info(f"Account deleted for {mobile}")
        return {"success": True, "message": "Account deleted successfully"}
    except Exception as e:
        logger.error(f"Error deleting account: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete account")
