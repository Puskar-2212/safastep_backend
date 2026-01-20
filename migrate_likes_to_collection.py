from database import posts_collection, likes_collection
import time

def migrate_likes():
    """
    Migrate likes from posts.likes array to separate likes collection
    """
    print("Starting likes migration...")
    
    migrated_count = 0
    posts_processed = 0
    
    # Get all posts that have likes
    posts_with_likes = posts_collection.find({"likes": {"$exists": True, "$ne": []}})
    
    for post in posts_with_likes:
        posts_processed += 1
        post_id = str(post["_id"])
        likes_array = post.get("likes", [])
        
        print(f"\nProcessing post {post_id} with {len(likes_array)} likes...")
        
        for user_id in likes_array:
            # Check if like already exists
            existing = likes_collection.find_one({
                "postId": post_id,
                "userId": user_id
            })
            
            if not existing:
                # Insert into likes collection
                likes_collection.insert_one({
                    "postId": post_id,
                    "userId": user_id,
                    "createdAt": post.get("createdAt", time.time())
                })
                migrated_count += 1
                print(f"  ✓ Migrated like from {user_id}")
            else:
                print(f"  - Like from {user_id} already exists, skipping")
        
        # Optional: Remove likes array from post (uncomment if you want to clean up)
        # posts_collection.update_one(
        #     {"_id": post["_id"]},
        #     {"$unset": {"likes": ""}}
        # )
    
    print(f"\n✅ Migration complete!")
    print(f"   Posts processed: {posts_processed}")
    print(f"   Likes migrated: {migrated_count}")
    print(f"\nTotal likes in collection: {likes_collection.count_documents({})}")

if __name__ == "__main__":
    migrate_likes()
