from pymongo import MongoClient

# MongoDB connection
MONGO_URI = "mongodb://localhost:27017"
mongo_client = MongoClient(MONGO_URI)

# Database and collections
user_db = mongo_client["users"]
users_collection = user_db["user_data"]
posts_collection = user_db["posts"]
carbon_footprints_collection = user_db["carbon_footprints"]
eco_locations_collection = user_db["eco_locations"]
