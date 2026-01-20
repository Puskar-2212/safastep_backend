from database import posts_collection

def cleanup_likes_array():
    """
    Remove the 'likes' array field from all posts since we now use a separate collection
    """
    print("Starting cleanup of likes array from posts collection...")
    
    # Count posts with likes array
    posts_with_likes_array = posts_collection.count_documents({"likes": {"$exists": True}})
    print(f"Found {posts_with_likes_array} posts with 'likes' array field")
    
    if posts_with_likes_array == 0:
        print("✅ No cleanup needed - all posts are already clean!")
        return
    
    # Remove likes array from all posts
    result = posts_collection.update_many(
        {"likes": {"$exists": True}},
        {"$unset": {"likes": ""}}
    )
    
    print(f"\n✅ Cleanup complete!")
    print(f"   Posts updated: {result.modified_count}")
    print(f"   Posts matched: {result.matched_count}")
    
    # Verify cleanup
    remaining = posts_collection.count_documents({"likes": {"$exists": True}})
    print(f"\nVerification:")
    print(f"   Posts still with 'likes' array: {remaining}")
    
    if remaining == 0:
        print("   ✅ All posts cleaned successfully!")
    else:
        print(f"   ⚠️  Warning: {remaining} posts still have 'likes' array")

if __name__ == "__main__":
    cleanup_likes_array()
