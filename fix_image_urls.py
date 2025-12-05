from database import posts_collection, users_collection
from config import BASE_URL
import re

print(f"Current BASE_URL: {BASE_URL}\n")

# Fix post images
posts = list(posts_collection.find())
print(f"Found {len(posts)} posts to check\n")

updated_posts = 0
for post in posts:
    old_url = post.get('imageUrl', '')
    if old_url:
        # Extract just the filename from the old URL
        filename = old_url.split('/uploads/')[-1]
        new_url = f"{BASE_URL}/uploads/{filename}"
        
        if old_url != new_url:
            posts_collection.update_one(
                {'_id': post['_id']},
                {'$set': {'imageUrl': new_url}}
            )
            print(f"Updated post {post['_id']}")
            print(f"  Old: {old_url}")
            print(f"  New: {new_url}\n")
            updated_posts += 1

print(f"✓ Updated {updated_posts} post images\n")

# Fix profile pictures
users = list(users_collection.find({'profilePicture': {'$exists': True}}))
print(f"Found {len(users)} users with profile pictures to check\n")

updated_users = 0
for user in users:
    old_url = user.get('profilePicture', '')
    if old_url:
        # Extract just the filename from the old URL
        filename = old_url.split('/uploads/')[-1]
        new_url = f"{BASE_URL}/uploads/{filename}"
        
        if old_url != new_url:
            users_collection.update_one(
                {'_id': user['_id']},
                {'$set': {'profilePicture': new_url}}
            )
            print(f"Updated user {user.get('mobile', user['_id'])}")
            print(f"  Old: {old_url}")
            print(f"  New: {new_url}\n")
            updated_users += 1

print(f"✓ Updated {updated_users} profile pictures")
print(f"\n✓ Migration complete! All image URLs now use: {BASE_URL}")
