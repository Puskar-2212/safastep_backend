from pymongo import MongoClient

# MongoDB connection with proper settings to prevent connection leaks
MONGO_URI = "mongodb://localhost:27017"
mongo_client = MongoClient(
    MONGO_URI,
    maxPoolSize=50,  # Maximum number of connections in the pool
    minPoolSize=10,  # Minimum number of connections in the pool
    maxIdleTimeMS=45000,  # Close connections after 45 seconds of inactivity
    serverSelectionTimeoutMS=5000,  # Timeout for server selection
    connectTimeoutMS=10000,  # Timeout for initial connection
    socketTimeoutMS=20000,  # Timeout for socket operations
)

# Database and collections
user_db = mongo_client["users"]
users_collection = user_db["user_data"]
posts_collection = user_db["posts"]
likes_collection = user_db["likes"]
carbon_footprints_collection = user_db["carbon_footprints"]
eco_locations_collection = user_db["eco_locations"]
notifications_collection = user_db["notifications"]
achievements_collection = user_db["achievements"]
user_achievements_collection = user_db["user_achievements"]

def close_mongo_connection():
    """Close MongoDB connection properly"""
    try:
        mongo_client.close()
        print("MongoDB connection closed successfully")
    except Exception as e:
        print(f"Error closing MongoDB connection: {e}")
