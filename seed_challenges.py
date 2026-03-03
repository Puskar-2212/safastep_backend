from database import user_db
from datetime import datetime

# Get collections
challenges_collection = user_db["challenges"]
user_challenges_collection = user_db["user_challenges"]

# Sample daily check-in challenges
challenges = [
    # QUICK CHALLENGES (1-3 days) - Can be completed quickly
    {
        "challenge_id": "quick_eco_pledge",
        "title": "Take the Eco Pledge",
        "description": "Commit to one eco-friendly action today",
        "type": "daily_checkin",
        "duration_days": 1,
        "reward_points": 50,
        "category": "general",
        "icon": "✋",
        "difficulty": "easy",
        "tips": [
            "Choose one simple action",
            "Make it realistic and achievable",
            "Share your commitment with friends",
            "Start small, think big"
        ],
        "active": True,
        "allow_one_skip": False,
        "created_at": datetime.utcnow()
    },
    {
        "challenge_id": "lights_out_today",
        "title": "Lights Out Challenge",
        "description": "Turn off unnecessary lights for one day",
        "type": "daily_checkin",
        "duration_days": 1,
        "reward_points": 30,
        "category": "energy",
        "icon": "💡",
        "difficulty": "easy",
        "tips": [
            "Use natural light during the day",
            "Turn off lights when leaving rooms",
            "Unplug devices not in use",
            "Use task lighting instead of overhead lights"
        ],
        "active": True,
        "allow_one_skip": False,
        "created_at": datetime.utcnow()
    },
    {
        "challenge_id": "water_bottle_day",
        "title": "Reusable Bottle Day",
        "description": "Use a reusable water bottle all day",
        "type": "daily_checkin",
        "duration_days": 1,
        "reward_points": 25,
        "category": "waste_management",
        "icon": "🥤",
        "difficulty": "easy",
        "tips": [
            "Fill your bottle before leaving home",
            "Keep it visible as a reminder",
            "Track how many plastic bottles you saved",
            "Clean it at the end of the day"
        ],
        "active": True,
        "allow_one_skip": False,
        "created_at": datetime.utcnow()
    },
    {
        "challenge_id": "no_plastic_bags_3day",
        "title": "3-Day No Plastic Bags",
        "description": "Use reusable bags for all shopping",
        "type": "daily_checkin",
        "duration_days": 3,
        "reward_points": 75,
        "category": "waste_management",
        "icon": "🛍️",
        "difficulty": "easy",
        "tips": [
            "Keep bags in your car or by the door",
            "Attach a small bag to your keychain",
            "Set a reminder before shopping",
            "Choose sturdy, washable bags"
        ],
        "active": True,
        "allow_one_skip": False,
        "created_at": datetime.utcnow()
    },
    {
        "challenge_id": "meatless_monday",
        "title": "Meatless Monday",
        "description": "Go vegetarian for one day",
        "type": "daily_checkin",
        "duration_days": 1,
        "reward_points": 40,
        "category": "food",
        "icon": "🥗",
        "difficulty": "easy",
        "tips": [
            "Try a new vegetarian recipe",
            "Explore plant-based proteins",
            "Visit a vegetarian restaurant",
            "Meal prep to make it easier"
        ],
        "active": True,
        "allow_one_skip": False,
        "created_at": datetime.utcnow()
    },
    {
        "challenge_id": "digital_detox_day",
        "title": "Digital Detox Day",
        "description": "Reduce screen time and save energy",
        "type": "daily_checkin",
        "duration_days": 1,
        "reward_points": 35,
        "category": "energy",
        "icon": "📱",
        "difficulty": "easy",
        "tips": [
            "Set screen time limits",
            "Unplug chargers when not in use",
            "Read a book instead",
            "Spend time outdoors"
        ],
        "active": True,
        "allow_one_skip": False,
        "created_at": datetime.utcnow()
    },
    
    # MEDIUM CHALLENGES (7-14 days)
    {
        "challenge_id": "plastic_free_7day",
        "title": "7-Day Plastic-Free Challenge",
        "description": "Avoid single-use plastic for 7 consecutive days",
        "type": "daily_checkin",
        "duration_days": 7,
        "reward_points": 200,
        "category": "waste_management",
        "icon": "🚫",
        "difficulty": "medium",
        "tips": [
            "Bring your own water bottle",
            "Use cloth bags for shopping",
            "Say no to plastic straws",
            "Choose products with minimal packaging"
        ],
        "active": True,
        "allow_one_skip": False,
        "created_at": datetime.utcnow()
    },
    {
        "challenge_id": "public_transport_14day",
        "title": "14-Day Public Transport Challenge",
        "description": "Use public transport, bike, or walk instead of personal vehicle",
        "type": "daily_checkin",
        "duration_days": 14,
        "reward_points": 400,
        "category": "transportation",
        "icon": "🚌",
        "difficulty": "hard",
        "tips": [
            "Plan your route in advance",
            "Combine trips to save time",
            "Try carpooling with colleagues",
            "Use bike-sharing services"
        ],
        "active": True,
        "allow_one_skip": True,
        "created_at": datetime.utcnow()
    },
    {
        "challenge_id": "zero_waste_7day",
        "title": "7-Day Zero-Waste Challenge",
        "description": "Minimize waste by refusing, reducing, reusing, and recycling",
        "type": "daily_checkin",
        "duration_days": 7,
        "reward_points": 250,
        "category": "waste_management",
        "icon": "♻️",
        "difficulty": "medium",
        "tips": [
            "Carry reusable containers",
            "Compost food scraps",
            "Buy in bulk to reduce packaging",
            "Repair instead of replace"
        ],
        "active": True,
        "allow_one_skip": False,
        "created_at": datetime.utcnow()
    },
    {
        "challenge_id": "energy_saver_7day",
        "title": "7-Day Energy Saver Challenge",
        "description": "Reduce energy consumption by turning off unused devices",
        "type": "daily_checkin",
        "duration_days": 7,
        "reward_points": 200,
        "category": "energy",
        "icon": "💡",
        "difficulty": "easy",
        "tips": [
            "Unplug chargers when not in use",
            "Use natural light during the day",
            "Turn off lights when leaving rooms",
            "Use energy-efficient appliances"
        ],
        "active": True,
        "allow_one_skip": False,
        "created_at": datetime.utcnow()
    },
    
    # HARD CHALLENGES (21-30 days)
    {
        "challenge_id": "reusable_bag_21day",
        "title": "21-Day Reusable Bag Challenge",
        "description": "Always use reusable bags for shopping",
        "type": "daily_checkin",
        "duration_days": 21,
        "reward_points": 600,
        "category": "waste_management",
        "icon": "🛍️",
        "difficulty": "medium",
        "tips": [
            "Keep bags in your car",
            "Attach a bag to your keychain",
            "Set reminders before shopping",
            "Choose durable, washable bags"
        ],
        "active": True,
        "allow_one_skip": True,
        "created_at": datetime.utcnow()
    },
    {
        "challenge_id": "vegetarian_30day",
        "title": "30-Day Vegetarian Challenge",
        "description": "Eat plant-based meals for 30 consecutive days",
        "type": "daily_checkin",
        "duration_days": 30,
        "reward_points": 1000,
        "category": "food",
        "icon": "🥗",
        "difficulty": "hard",
        "tips": [
            "Explore new vegetarian recipes",
            "Stock up on plant-based proteins",
            "Try meat alternatives",
            "Join vegetarian cooking groups"
        ],
        "active": True,
        "allow_one_skip": True,
        "created_at": datetime.utcnow()
    }
]

def seed_challenges():
    try:
        # Clear existing challenges
        challenges_collection.delete_many({"type": "daily_checkin"})
        
        # Insert new challenges
        result = challenges_collection.insert_many(challenges)
        
        print(f"✅ Successfully seeded {len(result.inserted_ids)} challenges!")
        print("\nChallenges added:")
        for challenge in challenges:
            print(f"  • {challenge['title']} ({challenge['duration_days']} days, {challenge['reward_points']} points)")
        
    except Exception as e:
        print(f"❌ Error seeding challenges: {e}")

if __name__ == "__main__":
    seed_challenges()
