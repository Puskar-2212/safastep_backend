"""
Script to migrate existing local images to Cloudinary
Run this after setting up Cloudinary credentials in .env
"""
import os
import logging
from database import users_collection, posts_collection
from utils.cloudinary_upload import upload_image_to_cloudinary
from config import UPLOAD_DIR

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def migrate_images():
    """Migrate all local images to Cloudinary and update database"""
    
    migrated_count = 0
    failed_count = 0
    
    # Migrate post images
    logger.info("Starting migration of post images...")
    posts = list(posts_collection.find({"imageFilename": {"$exists": True}}))
    
    for post in posts:
        try:
            filename = post.get("imageFilename")
            if not filename:
                continue
            
            file_path = os.path.join(UPLOAD_DIR, filename)
            
            if not os.path.exists(file_path):
                logger.warning(f"File not found: {file_path}")
                failed_count += 1
                continue
            
            # Upload to Cloudinary in "posts" folder
            result = upload_image_to_cloudinary(
                file_path, 
                folder="safastep/posts",
                public_id=filename.split('.')[0]  # Use filename without extension as public_id
            )
            
            if result["success"]:
                # Update post with Cloudinary URL
                posts_collection.update_one(
                    {"_id": post["_id"]},
                    {
                        "$set": {
                            "imageUrl": result["url"],
                            "cloudinaryPublicId": result["public_id"]
                        }
                    }
                )
                logger.info(f"Migrated post image: {filename} -> {result['url']}")
                migrated_count += 1
            else:
                logger.error(f"Failed to upload {filename}: {result.get('error')}")
                failed_count += 1
                
        except Exception as e:
            logger.error(f"Error migrating post image {filename}: {e}")
            failed_count += 1
    
    # Migrate profile pictures
    logger.info("Starting migration of profile pictures...")
    users = list(users_collection.find({"profilePictureFilename": {"$exists": True}}))
    
    for user in users:
        try:
            filename = user.get("profilePictureFilename")
            if not filename:
                continue
            
            file_path = os.path.join(UPLOAD_DIR, filename)
            
            if not os.path.exists(file_path):
                logger.warning(f"File not found: {file_path}")
                failed_count += 1
                continue
            
            # Upload to Cloudinary in "profiles" folder
            result = upload_image_to_cloudinary(
                file_path,
                folder="safastep/profiles",
                public_id=filename.split('.')[0]
            )
            
            if result["success"]:
                # Update user with Cloudinary URL
                users_collection.update_one(
                    {"_id": user["_id"]},
                    {
                        "$set": {
                            "profilePicture": result["url"],
                            "cloudinaryPublicId": result["public_id"]
                        }
                    }
                )
                logger.info(f"Migrated profile picture: {filename} -> {result['url']}")
                migrated_count += 1
            else:
                logger.error(f"Failed to upload {filename}: {result.get('error')}")
                failed_count += 1
                
        except Exception as e:
            logger.error(f"Error migrating profile picture {filename}: {e}")
            failed_count += 1
    
    logger.info(f"\nMigration complete!")
    logger.info(f"Successfully migrated: {migrated_count} images")
    logger.info(f"Failed: {failed_count} images")
    logger.info(f"\nYou can now delete local images from the uploads/ folder")

if __name__ == "__main__":
    print("=" * 60)
    print("Cloudinary Migration Script")
    print("=" * 60)
    print("\nThis will upload all local images to Cloudinary")
    print("Make sure you have set up Cloudinary credentials in .env file:")
    print("  - CLOUDINARY_CLOUD_NAME")
    print("  - CLOUDINARY_API_KEY")
    print("  - CLOUDINARY_API_SECRET")
    print("\n" + "=" * 60)
    
    response = input("\nDo you want to continue? (yes/no): ")
    
    if response.lower() in ['yes', 'y']:
        migrate_images()
    else:
        print("Migration cancelled.")
