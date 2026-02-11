"""
Setup script for eco_locations collection indexes
Run this once to create the necessary indexes for geospatial queries
"""

from database import eco_locations_collection
from pymongo import GEOSPHERE, ASCENDING

def setup_indexes():
    """Create indexes for eco_locations collection"""
    
    print("Setting up indexes for eco_locations collection...")
    
    # Create 2dsphere geospatial index for location field
    eco_locations_collection.create_index([("location", GEOSPHERE)])
    print("Created 2dsphere index on 'location' field")
    
    # Create compound index for filtering by city, category, and status
    eco_locations_collection.create_index([
        ("city", ASCENDING),
        ("category", ASCENDING),
        ("status", ASCENDING)
    ])
    print("✓ Created compound index on (city, category, status)")
    
    # Create index on eventDate for event queries
    eco_locations_collection.create_index([("eventDate", ASCENDING)])
    print("Created index on 'eventDate' field")
    
    # List all indexes
    print("\nAll indexes on eco_locations:")
    for index in eco_locations_collection.list_indexes():
        print(f"  - {index['name']}: {index['key']}")
    
    print("\n Index setup complete!")

if __name__ == "__main__":
    setup_indexes()
