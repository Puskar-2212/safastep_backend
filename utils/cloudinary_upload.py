import cloudinary
import cloudinary.uploader
import os
import logging
from config import CLOUDINARY_CLOUD_NAME, CLOUDINARY_API_KEY, CLOUDINARY_API_SECRET

logger = logging.getLogger(__name__)

# Configure Cloudinary
cloudinary.config(
    cloud_name=CLOUDINARY_CLOUD_NAME,
    api_key=CLOUDINARY_API_KEY,
    api_secret=CLOUDINARY_API_SECRET
)

def upload_image_to_cloudinary(file_path: str, folder: str = "safastep", public_id: str = None) -> dict:
    """
    Upload an image to Cloudinary
    
    Args:
        file_path: Local path to the image file
        folder: Cloudinary folder to organize images (default: "safastep")
        public_id: Optional custom public ID for the image
    
    Returns:
        dict with success status, url, and public_id
    """
    try:
        # Upload options
        upload_options = {
            "folder": folder,
            "resource_type": "image",
            "quality": "auto",
            "fetch_format": "auto"
        }
        
        if public_id:
            upload_options["public_id"] = public_id
        
        # Upload to Cloudinary
        result = cloudinary.uploader.upload(file_path, **upload_options)
        
        logger.info(f"Image uploaded to Cloudinary: {result['secure_url']}")
        
        return {
            "success": True,
            "url": result["secure_url"],
            "public_id": result["public_id"],
            "format": result["format"],
            "width": result["width"],
            "height": result["height"]
        }
        
    except Exception as e:
        logger.error(f"Error uploading to Cloudinary: {e}")
        return {
            "success": False,
            "error": str(e)
        }

def delete_image_from_cloudinary(public_id: str) -> dict:
    """
    Delete an image from Cloudinary
    
    Args:
        public_id: The public ID of the image to delete
    
    Returns:
        dict with success status
    """
    try:
        result = cloudinary.uploader.destroy(public_id)
        
        if result.get("result") == "ok":
            logger.info(f"Image deleted from Cloudinary: {public_id}")
            return {"success": True}
        else:
            logger.warning(f"Failed to delete image from Cloudinary: {public_id}")
            return {"success": False, "error": "Image not found or already deleted"}
            
    except Exception as e:
        logger.error(f"Error deleting from Cloudinary: {e}")
        return {
            "success": False,
            "error": str(e)
        }

def get_cloudinary_url(public_id: str, transformation: dict = None) -> str:
    """
    Generate a Cloudinary URL with optional transformations
    
    Args:
        public_id: The public ID of the image
        transformation: Optional dict of transformations (width, height, crop, etc.)
    
    Returns:
        Cloudinary URL string
    """
    try:
        if transformation:
            url, _ = cloudinary.utils.cloudinary_url(public_id, **transformation)
        else:
            url, _ = cloudinary.utils.cloudinary_url(public_id)
        
        return url
        
    except Exception as e:
        logger.error(f"Error generating Cloudinary URL: {e}")
        return None
