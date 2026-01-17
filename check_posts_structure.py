from database import posts_collection
import json

def check_posts_structure():
    """
    Check the structure of posts in the database
    """
    print("Checking posts collection structure...\n")
    
    # Count total posts
    total_posts = posts_collection.count_documents({})
    print(f"Total posts in database: {total_posts}\n")
    
    if total_posts == 0:
        print("No posts found in database.")
        return
    
    # Get a sample post
    sample_post = posts_collection.find_one()
    
    if sample_post:
        print("Sample post structure:")
        print("=" * 50)
        
        # Convert ObjectId to string for display
        if "_id" in sample_post:
            sample_post["_id"] = str(sample_post["_id"])
        
        # Pretty print the structure
        for key, value in sample_post.items():
            if isinstance(value, list) and len(value) > 3:
                print(f"  {key}: [{len(value)} items]")
            elif isinstance(value, dict):
                print(f"  {key}: {{...}}")
            else:
                print(f"  {key}: {value}")
        
        print("=" * 50)
        
        # Check for unnecessary fields
        print("\nField Analysis:")
        if "likes" in sample_post:
            print("  ⚠️  'likes' array found - SHOULD BE REMOVED")
        else:
            print("  ✅ 'likes' array not found - GOOD")
        
        if "likesCount" in sample_post:
            print(f"  ✅ 'likesCount' found: {sample_post['likesCount']}")
        else:
            print("  ⚠️  'likesCount' not found")
        
        if "comments" in sample_post:
            comments_count = len(sample_post["comments"]) if isinstance(sample_post["comments"], list) else 0
            print(f"  ℹ️  'comments' array found with {comments_count} items")
        
        if "commentsCount" in sample_post:
            print(f"  ✅ 'commentsCount' found: {sample_post['commentsCount']}")

if __name__ == "__main__":
    check_posts_structure()
