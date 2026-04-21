#!/usr/bin/env python3
"""
Seed script for achievements in SafaStep
Run this script to populate the achievements collection with initial badge data.
"""

from database import achievements_collection
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

ACHIEVEMENTS = [
    {
        "id": "eco_starter",
        "name": "Eco Starter",
        "description": "Earn 200 eco points",
        "iconUrl": "/assets/badges/eco_starter.svg",
        "condition": {"type": "eco_points", "value": 200}
    },
    {
        "id": "eco_enthusiast",
        "name": "Eco Enthusiast",
        "description": "Earn 500 eco points",
        "iconUrl": "/assets/badges/eco_enthusiast.svg",
        "condition": {"type": "eco_points", "value": 500}
    },
    {
        "id": "eco_champion",
        "name": "Eco Champion",
        "description": "Earn 1000 eco points",
        "iconUrl": "/assets/badges/eco_champion.svg",
        "condition": {"type": "eco_points", "value": 1000}
    },
    {
        "id": "first_step",
        "name": "First Step",
        "description": "Create your first post",
        "iconUrl": "/assets/badges/first_step.svg",
        "condition": {"type": "posts", "value": 1}
    },
    {
        "id": "eco_contributor",
        "name": "Eco Contributor",
        "description": "Create 10 posts",
        "iconUrl": "/assets/badges/eco_contributor.svg",
        "condition": {"type": "posts", "value": 10}
    },
    {
        "id": "eco_influencer",
        "name": "Eco Influencer",
        "description": "Create 50 posts",
        "iconUrl": "/assets/badges/eco_influencer.svg",
        "condition": {"type": "posts", "value": 50}
    }
]

def seed_achievements():
    """Seed the achievements collection with initial data"""
    try:
        # Clear existing achievements
        achievements_collection.delete_many({})
        logger.info("Cleared existing achievements")

        # Insert new achievements
        result = achievements_collection.insert_many(ACHIEVEMENTS)
        logger.info(f"Inserted {len(result.inserted_ids)} achievements")

        # Verify insertion
        count = achievements_collection.count_documents({})
        logger.info(f"Total achievements in collection: {count}")

        print("✅ Achievements seeded successfully!")
        return True

    except Exception as e:
        logger.error(f"Error seeding achievements: {e}")
        print(f"❌ Error seeding achievements: {e}")
        return False

if __name__ == "__main__":
    seed_achievements()