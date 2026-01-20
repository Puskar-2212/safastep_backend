from database import likes_collection

def setup_likes_indexes():
    """
    Create indexes for the likes collection for better query performance
    """
    print("Setting up indexes for likes collection...")
    
    # Create compound index on postId and userId for fast lookup
    likes_collection.create_index([("postId", 1), ("userId", 1)], unique=True)
    print("✓ Created compound index on (postId, userId)")
    
    # Create index on postId for getting all likes for a post
    likes_collection.create_index([("postId", 1)])
    print("✓ Created index on postId")
    
    # Create index on userId for getting all posts liked by a user
    likes_collection.create_index([("userId", 1)])
    print("✓ Created index on userId")
    
    # Create index on createdAt for sorting
    likes_collection.create_index([("createdAt", -1)])
    print("✓ Created index on createdAt")
    
    print("\n✅ All indexes created successfully!")
    print("\nIndexes:")
    for index in likes_collection.list_indexes():
        print(f"  - {index['name']}: {index['key']}")

if __name__ == "__main__":
    setup_likes_indexes()
